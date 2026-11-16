interface TableSnapshot {
  name: string;
  count: number;
  rows: Record<string, unknown>[];
}

interface DatabaseSnapshot {
  path: string;
  size_bytes: number | null;
  tables: TableSnapshot[];
}

interface BridgeReply {
  data?: DatabaseSnapshot;
  saved_to?: string;
  cancelled?: boolean;
  error?: string;
}

interface DatabaseBridge {
  snapshot(callback: (reply: string) => void): void;
  backup(callback: (reply: string) => void): void;
  export_table(tableName: string, callback: (reply: string) => void): void;
  check_integrity(callback: (reply: string) => void): void;
}

declare const qt: { webChannelTransport: unknown };
declare const QWebChannel: new (
  transport: unknown,
  ready: (channel: { objects: { databaseBridge: DatabaseBridge } }) => void,
) => void;

const elements = {
  status: document.querySelector<HTMLElement>("#status")!,
  path: document.querySelector<HTMLElement>("#database-path")!,
  size: document.querySelector<HTMLElement>("#database-size")!,
  total: document.querySelector<HTMLElement>("#record-count")!,
  tabs: document.querySelector<HTMLElement>("#table-tabs")!,
  title: document.querySelector<HTMLElement>("#table-title")!,
  filter: document.querySelector<HTMLInputElement>("#filter")!,
  pageSize: document.querySelector<HTMLSelectElement>("#page-size")!,
  rowCount: document.querySelector<HTMLElement>("#row-count")!,
  pageLabel: document.querySelector<HTMLElement>("#page-label")!,
  head: document.querySelector<HTMLTableSectionElement>("#table-head")!,
  body: document.querySelector<HTMLTableSectionElement>("#table-body")!,
  empty: document.querySelector<HTMLElement>("#empty")!,
  refresh: document.querySelector<HTMLButtonElement>("#refresh")!,
  integrity: document.querySelector<HTMLButtonElement>("#integrity")!,
  export: document.querySelector<HTMLButtonElement>("#export")!,
  backup: document.querySelector<HTMLButtonElement>("#backup")!,
  previous: document.querySelector<HTMLButtonElement>("#page-previous")!,
  next: document.querySelector<HTMLButtonElement>("#page-next")!,
};

let bridge: DatabaseBridge;
let snapshot: DatabaseSnapshot | null = null;
let selectedTable = "";
let loading = false;
let page = 0;
let sortColumn = "";
let descending = true;
let expandedRow: string | null = null;

function setStatus(message: string, state: "normal" | "error" | "success" = "normal"): void {
  elements.status.textContent = message;
  elements.status.className = `status${state === "normal" ? "" : ` ${state}`}`;
}

function decodeReply(raw: string): BridgeReply {
  try {
    const reply: unknown = JSON.parse(raw);
    if (typeof reply !== "object" || reply === null) {
      throw new Error("The app returned an invalid response.");
    }
    return reply as BridgeReply;
  } catch (error) {
    throw new Error(error instanceof Error ? error.message : "The app returned invalid data.");
  }
}

function invoke<T>(call: (callback: (raw: string) => void) => void): Promise<T> {
  return new Promise((resolve, reject) => {
    call((raw) => {
      try {
        const reply = decodeReply(raw);
        if (reply.error) {
          reject(new Error(reply.error));
        } else {
          resolve(reply as T);
        }
      } catch (error) {
        reject(error);
      }
    });
  });
}

function tableData(): TableSnapshot | undefined {
  return snapshot?.tables.find((table) => table.name === selectedTable);
}

function updateSummary(): void {
  if (!snapshot) return;
  elements.path.textContent = snapshot.path;
  elements.path.title = snapshot.path;
  elements.size.textContent = DatabaseModel.formatSize(snapshot.size_bytes);
  elements.total.textContent = DatabaseModel.totalRecords(snapshot.tables).toLocaleString();
}

function renderTabs(): void {
  if (!snapshot) return;
  elements.tabs.replaceChildren();
  for (const table of snapshot.tables) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = `${table.name.split("_").join(" ")} (${table.count.toLocaleString()})`;
    button.setAttribute("aria-selected", String(table.name === selectedTable));
    button.addEventListener("click", () => {
      selectedTable = table.name;
      page = 0;
      renderTabs();
      renderRows();
    });
    elements.tabs.append(button);
  }
}

function visibleRows(table: TableSnapshot): Record<string, unknown>[] {
  const filtered = DatabaseModel.filterRows(table.rows, elements.filter.value);
  return DatabaseModel.sortRows(filtered, sortColumn, descending);
}

function renderRows(): void {
  const table = tableData();
  elements.head.replaceChildren();
  elements.body.replaceChildren();
  if (!table) {
    elements.title.textContent = "Database";
    elements.rowCount.textContent = "";
    elements.pageLabel.textContent = "";
    elements.empty.hidden = false;
    elements.export.disabled = true;
    elements.previous.disabled = true;
    elements.next.disabled = true;
    return;
  }

  elements.title.textContent = table.name.split("_").join(" ");
  const matchingRows = visibleRows(table);
  const slice = DatabaseModel.paginate(
    matchingRows,
    page,
    Number(elements.pageSize.value),
  );
  page = slice.current;
  const rows = slice.items;
  const columns = Object.keys(matchingRows[0] ?? table.rows[0] ?? {});
  const header = document.createElement("tr");
  for (const column of columns) {
    const cell = document.createElement("th");
    cell.scope = "col";
    const sort = document.createElement("button");
    sort.type = "button";
    sort.className = "sort-button";
    sort.textContent = `${column.split("_").join(" ")}${sortColumn === column ? (descending ? " v" : " ^") : ""}`;
    sort.setAttribute("aria-sort", sortColumn !== column ? "none" : descending ? "descending" : "ascending");
    sort.addEventListener("click", () => {
      if (sortColumn === column) descending = !descending;
      else {
        sortColumn = column;
        descending = false;
      }
      page = 0;
      renderRows();
    });
    cell.append(sort);
    header.append(cell);
  }
  elements.head.append(header);

  for (const row of rows) {
    const tr = document.createElement("tr");
    for (const column of columns) {
      const td = document.createElement("td");
      const text = DatabaseModel.cellText(row[column]);
      td.textContent = text;
      td.title = text;
      tr.append(td);
    }
    const detailsCell = document.createElement("td");
    const key = `${slice.firstIndex + rows.indexOf(row)}:${JSON.stringify(row) ?? ""}`;
    const inspect = document.createElement("button");
    inspect.type = "button";
    inspect.className = "inspect-button";
    inspect.textContent = expandedRow === key ? "Hide" : "View";
    inspect.setAttribute("aria-expanded", String(expandedRow === key));
    inspect.addEventListener("click", () => {
      expandedRow = expandedRow === key ? null : key;
      renderRows();
    });
    detailsCell.append(inspect);
    tr.append(detailsCell);
    elements.body.append(tr);
    if (expandedRow === key) {
      const detailsRow = document.createElement("tr");
      detailsRow.className = "detail-row";
      const detailsCell = document.createElement("td");
      detailsCell.colSpan = columns.length + 1;
      const pre = document.createElement("pre");
      pre.textContent = JSON.stringify(row, null, 2);
      detailsCell.append(pre);
      detailsRow.append(detailsCell);
      elements.body.append(detailsRow);
    }
  }

  const actionHeader = document.createElement("th");
  actionHeader.scope = "col";
  actionHeader.textContent = "Details";
  header.append(actionHeader);
  elements.empty.hidden = matchingRows.length > 0;
  elements.empty.textContent = table.count === 0
    ? "No records in this table yet."
    : "No visible rows match this filter.";
  elements.rowCount.textContent = `${matchingRows.length} matching / ${table.count.toLocaleString()} total`;
  elements.pageLabel.textContent = `Page ${page + 1} of ${slice.count}`;
  elements.previous.disabled = page === 0;
  elements.next.disabled = page >= slice.count - 1;
  elements.export.disabled = table.count === 0;
}

async function refresh(): Promise<void> {
  if (loading) return;
  loading = true;
  elements.refresh.disabled = true;
  setStatus("Reading saved records...");
  try {
    const reply = await invoke<BridgeReply>((callback) => bridge.snapshot(callback));
    if (!DatabaseModel.isValidSnapshot(reply.data)) {
      throw new Error("The app returned an invalid database snapshot.");
    }
    snapshot = reply.data;
    if (!snapshot.tables.some((table) => table.name === selectedTable)) {
      selectedTable = snapshot.tables[0]?.name ?? "";
    }
    page = 0;
    expandedRow = null;
    updateSummary();
    renderTabs();
    renderRows();
    setStatus("Database is up to date.");
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "Could not read the database.", "error");
  } finally {
    loading = false;
    elements.refresh.disabled = false;
  }
}

async function backup(): Promise<void> {
  elements.backup.disabled = true;
  setStatus("Preparing database backup...");
  try {
    const reply = await invoke<BridgeReply>((callback) => bridge.backup(callback));
    if (reply.cancelled) {
      setStatus("Backup cancelled.");
    } else if (reply.saved_to) {
      setStatus(`Backup saved to ${reply.saved_to}`, "success");
    } else {
      throw new Error("The app did not confirm the backup location.");
    }
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "Could not back up the database.", "error");
  } finally {
    elements.backup.disabled = false;
  }
}

async function exportTable(): Promise<void> {
  const table = tableData();
  if (!table) return;
  elements.export.disabled = true;
  setStatus(`Preparing ${table.name} CSV...`);
  try {
    const reply = await invoke<BridgeReply>((callback) =>
      bridge.export_table(table.name, callback));
    if (reply.cancelled) {
      setStatus("Export cancelled.");
    } else if (reply.saved_to) {
      setStatus(`CSV saved to ${reply.saved_to}`, "success");
    } else {
      throw new Error("The app did not confirm the export location.");
    }
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "Could not export the table.", "error");
  } finally {
    elements.export.disabled = table.count === 0;
  }
}

async function checkIntegrity(): Promise<void> {
  elements.integrity.disabled = true;
  setStatus("Checking SQLite database integrity...");
  try {
    const reply = await invoke<{ integrity: string[] }>((callback) =>
      bridge.check_integrity(callback));
    if (reply.integrity.length === 1 && reply.integrity[0] === "ok") {
      setStatus("SQLite integrity check passed.", "success");
    } else {
      setStatus(`SQLite reported: ${reply.integrity.join("; ")}`, "error");
    }
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "Integrity check failed.", "error");
  } finally {
    elements.integrity.disabled = false;
  }
}

elements.filter.addEventListener("input", () => {
  page = 0;
  expandedRow = null;
  renderRows();
});
elements.pageSize.addEventListener("change", () => {
  page = 0;
  renderRows();
});
elements.refresh.addEventListener("click", () => void refresh());
elements.integrity.addEventListener("click", () => void checkIntegrity());
elements.export.addEventListener("click", () => void exportTable());
elements.backup.addEventListener("click", () => void backup());
elements.previous.addEventListener("click", () => {
  page = Math.max(0, page - 1);
  renderRows();
});
elements.next.addEventListener("click", () => {
  page += 1;
  renderRows();
});
new QWebChannel(qt.webChannelTransport, (channel) => {
  bridge = channel.objects.databaseBridge;
  void refresh();
});
