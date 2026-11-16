use std::fs::{self, File};
use std::io::{Read, Seek, SeekFrom};
use std::path::{Path, PathBuf};
use std::time::UNIX_EPOCH;

use pyo3::exceptions::{PyIOError, PyOSError};
use pyo3::prelude::*;
use serde_json::Value;

fn parse_json_line(line: &str) -> Option<Value> {
    let trimmed = line.trim();
    if trimmed.is_empty() {
        return None;
    }
    serde_json::from_str(trimmed).ok()
}

fn find_journal_files(directory: &Path) -> PyResult<Vec<String>> {
    if !directory.is_dir() {
        return Ok(Vec::new());
    }

    let mut files = Vec::new();
    for entry in fs::read_dir(directory).map_err(|error| PyOSError::new_err(error.to_string()))? {
        let entry = entry.map_err(|error| PyOSError::new_err(error.to_string()))?;
        let path = entry.path();
        let Some(name) = path.file_name().and_then(|value| value.to_str()) else {
            continue;
        };
        if !name.starts_with("Journal.") || !name.ends_with(".log") {
            continue;
        }

        let metadata = entry
            .metadata()
            .map_err(|error| PyOSError::new_err(error.to_string()))?;
        if metadata.is_file() {
            let modified = metadata.modified().unwrap_or(UNIX_EPOCH);
            files.push((
                modified,
                name.to_owned(),
                path.to_string_lossy().into_owned(),
            ));
        }
    }
    files.sort_by(|left, right| left.0.cmp(&right.0).then(left.1.cmp(&right.1)));
    Ok(files.into_iter().map(|(_, _, path)| path).collect())
}

#[pyfunction]
fn journal_files(directory: String) -> PyResult<Vec<String>> {
    find_journal_files(Path::new(&directory))
}

const MAX_PENDING_BYTES: usize = 8 * 1024 * 1024;

#[pyclass]
struct JournalTailReader {
    path: PathBuf,
    position: u64,
    pending: Vec<u8>,
    discarding_oversized_line: bool,
}

impl JournalTailReader {
    fn read_json_values(&mut self) -> PyResult<Vec<Value>> {
        let mut file =
            File::open(&self.path).map_err(|error| PyIOError::new_err(error.to_string()))?;
        let file_size = file
            .metadata()
            .map_err(|error| PyIOError::new_err(error.to_string()))?
            .len();
        if file_size < self.position {
            self.reset_state();
        }

        file.seek(SeekFrom::Start(self.position))
            .map_err(|error| PyIOError::new_err(error.to_string()))?;
        let mut chunk = Vec::new();
        let bytes_read = file
            .read_to_end(&mut chunk)
            .map_err(|error| PyIOError::new_err(error.to_string()))?;
        self.position += bytes_read as u64;
        self.pending.extend_from_slice(&chunk);

        let mut events = Vec::new();
        let mut line_start = 0;
        for (index, byte) in self.pending.iter().enumerate() {
            if index - line_start > MAX_PENDING_BYTES {
                self.discarding_oversized_line = true;
            }
            if *byte == b'\n' {
                let line = String::from_utf8_lossy(&self.pending[line_start..index])
                    .trim_end_matches('\r')
                    .to_owned();
                if !self.discarding_oversized_line {
                    if let Some(value) = parse_json_line(&line) {
                        events.push(value);
                    }
                }
                line_start = index + 1;
                self.discarding_oversized_line = false;
            }
        }
        self.pending.drain(..line_start);
        if self.pending.len() > MAX_PENDING_BYTES {
            self.pending.clear();
            self.discarding_oversized_line = true;
        }
        Ok(events)
    }

    fn reset_state(&mut self) {
        self.position = 0;
        self.pending.clear();
        self.discarding_oversized_line = false;
    }
}

#[pymethods]
impl JournalTailReader {
    #[new]
    fn new(path: String) -> Self {
        Self {
            path: PathBuf::from(path),
            position: 0,
            pending: Vec::new(),
            discarding_oversized_line: false,
        }
    }

    #[getter]
    fn position(&self) -> u64 {
        self.position
    }

    #[setter]
    fn set_position(&mut self, value: u64) {
        self.position = value;
        self.pending.clear();
        self.discarding_oversized_line = false;
    }

    fn reset(&mut self) {
        self.reset_state();
    }

    fn read_new_events(&mut self, py: Python<'_>) -> PyResult<Vec<Py<PyAny>>> {
        self.read_json_values()?
            .iter()
            .map(|value| Ok(pythonize::pythonize(py, value)?.unbind()))
            .collect()
    }
}

#[pymodule]
fn journal_native(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<JournalTailReader>()?;
    module.add_function(wrap_pyfunction!(journal_files, module)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::io::Write;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn temp_file() -> (PathBuf, File) {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let path =
            std::env::temp_dir().join(format!("edbio-journal-{}-{nonce}.log", std::process::id()));
        let file = File::create(&path).unwrap();
        (path, file)
    }

    #[test]
    fn reads_complete_lines_and_keeps_partial_tail() {
        let (path, mut file) = temp_file();
        file.write_all(b"{\"event\":\"Scan\"}\n{\"event\":\"Loc")
            .unwrap();
        drop(file);

        let mut reader = JournalTailReader::new(path.to_string_lossy().into_owned());
        let first = reader.read_json_values().unwrap();
        assert_eq!(first.len(), 1);
        assert_eq!(first[0]["event"], "Scan");

        let mut file = fs::OpenOptions::new().append(true).open(&path).unwrap();
        file.write_all(b"ation\"}\nnot-json\n{\"event\":\"Location\"}\n")
            .unwrap();
        drop(file);
        let events = reader.read_json_values().unwrap();
        assert_eq!(events.len(), 2);
        assert_eq!(events[0]["event"], "Location");
        fs::remove_file(path).unwrap();
    }

    #[test]
    fn truncation_restarts_from_the_new_file_contents() {
        let (path, mut file) = temp_file();
        file.write_all(b"old contents that are longer than a new journal\n")
            .unwrap();
        drop(file);

        let mut reader = JournalTailReader::new(path.to_string_lossy().into_owned());
        let original = reader.read_json_values().unwrap();
        assert!(original.is_empty());
        fs::write(&path, b"{\"event\":\"L\"}\n").unwrap();
        let updated = reader.read_json_values().unwrap();
        assert_eq!(updated.len(), 1);
        assert_eq!(updated[0]["event"], "L");
        fs::remove_file(path).unwrap();
    }

    #[test]
    fn ignores_malformed_json_lines() {
        assert!(parse_json_line("{not json").is_none());
        assert!(parse_json_line("  ").is_none());
        assert_eq!(
            parse_json_line("{\"event\":\"Scan\"}").unwrap()["event"],
            "Scan"
        );
    }

    #[test]
    fn sorts_journals_by_write_time_and_skips_non_journals() {
        let directory = std::env::temp_dir().join(format!("edbio-journals-{}", std::process::id()));
        fs::create_dir_all(&directory).unwrap();
        let oldest = directory.join("Journal.z.log");
        let newest = directory.join("Journal.a.log");
        fs::write(&oldest, b"").unwrap();
        std::thread::sleep(std::time::Duration::from_millis(25));
        fs::write(&newest, b"").unwrap();
        fs::write(directory.join("not-a-journal.log"), b"").unwrap();

        let paths = find_journal_files(&directory).unwrap();
        assert_eq!(paths.len(), 2);
        assert!(paths[0].ends_with("Journal.z.log"));
        assert!(paths[1].ends_with("Journal.a.log"));
        fs::remove_dir_all(directory).unwrap();
    }

    #[test]
    fn oversized_partial_line_is_discarded_until_the_next_line() {
        let (path, mut file) = temp_file();
        let mut content = vec![b'x'; MAX_PENDING_BYTES + 1];
        content.extend_from_slice(b"\n{\"event\":\"Scan\"}\n");
        file.write_all(&content).unwrap();
        drop(file);

        let mut reader = JournalTailReader::new(path.to_string_lossy().into_owned());
        let events = reader.read_json_values().unwrap();
        assert_eq!(events.len(), 1);
        assert_eq!(events[0]["event"], "Scan");
        fs::remove_file(path).unwrap();
    }

    #[test]
    fn missing_journal_directory_returns_no_files() {
        let directory = std::env::temp_dir().join(format!("edbio-missing-{}", std::process::id()));
        assert!(find_journal_files(&directory).unwrap().is_empty());
    }
}
