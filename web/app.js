"use strict";
var DatabaseModel;
(function (DatabaseModel) {
    function cellText(value) {
        if (value === null || value === undefined)
            return "";
        if (typeof value === "object")
            return JSON.stringify(value);
        return String(value);
    }
    DatabaseModel.cellText = cellText;
    function filterRows(rows, query) {
        const normalized = query.trim().toLocaleLowerCase();
        if (!normalized)
            return rows.slice();
        return rows.filter((row) => Object.values(row).some((value) => cellText(value).toLocaleLowerCase().includes(normalized)));
    }
    DatabaseModel.filterRows = filterRows;
    function compareValues(left, right) {
        if (typeof left === "number" && typeof right === "number")
            return left - right;
        return cellText(left).localeCompare(cellText(right), undefined, {
            numeric: true,
            sensitivity: "base",
        });
    }
    DatabaseModel.compareValues = compareValues;
    function sortRows(rows, column, descending) {
        if (!column)
            return rows.slice();
        const sorted = rows.slice().sort((left, right) => compareValues(left[column], right[column]));
        return descending ? sorted.reverse() : sorted;
    }
    DatabaseModel.sortRows = sortRows;
    function paginate(rows, page, pageSize) {
        const safePageSize = Number.isFinite(pageSize) ? Math.max(1, Math.floor(pageSize)) : 1;
        const count = Math.max(1, Math.ceil(rows.length / safePageSize));
        const current = Math.max(0, Math.min(Math.floor(page) || 0, count - 1));
        const firstIndex = current * safePageSize;
        return {
            items: rows.slice(firstIndex, firstIndex + safePageSize),
            current,
            count,
            firstIndex,
        };
    }
    DatabaseModel.paginate = paginate;
    function formatSize(bytes) {
        if (bytes === null)
            return "In-memory";
        if (bytes < 1024)
            return `${bytes} bytes`;
        if (bytes < 1024 * 1024)
            return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    }
    DatabaseModel.formatSize = formatSize;
    function totalRecords(tables) {
        return tables.reduce((sum, table) => sum + table.count, 0);
    }
    DatabaseModel.totalRecords = totalRecords;
    function isValidSnapshot(value) {
        if (typeof value !== "object" || value === null)
            return false;
        const candidate = value;
        if (typeof candidate.path !== "string" || !Array.isArray(candidate.tables))
            return false;
        if (candidate.size_bytes !== null && typeof candidate.size_bytes !== "number")
            return false;
        return candidate.tables.every((table) => {
            if (typeof table !== "object" || table === null)
                return false;
            const item = table;
            return typeof item.name === "string"
                && Number.isInteger(item.count)
                && Number(item.count) >= 0
                && Array.isArray(item.rows)
                && item.rows.every((row) => typeof row === "object" && row !== null);
        });
    }
    DatabaseModel.isValidSnapshot = isValidSnapshot;
})(DatabaseModel || (DatabaseModel = {}));
const elements = {
    status: document.querySelector("#status"),
    path: document.querySelector("#database-path"),
    size: document.querySelector("#database-size"),
    total: document.querySelector("#record-count"),
    tabs: document.querySelector("#table-tabs"),
    title: document.querySelector("#table-title"),
    filter: document.querySelector("#filter"),
    pageSize: document.querySelector("#page-size"),
    rowCount: document.querySelector("#row-count"),
    pageLabel: document.querySelector("#page-label"),
    head: document.querySelector("#table-head"),
    body: document.querySelector("#table-body"),
    empty: document.querySelector("#empty"),
    refresh: document.querySelector("#refresh"),
    integrity: document.querySelector("#integrity"),
    export: document.querySelector("#export"),
    backup: document.querySelector("#backup"),
    previous: document.querySelector("#page-previous"),
    next: document.querySelector("#page-next"),
};
let bridge;
let snapshot = null;
let selectedTable = "";
let loading = false;
let page = 0;
let sortColumn = "";
let descending = true;
let expandedRow = null;
function setStatus(message, state = "normal") {
    elements.status.textContent = message;
    elements.status.className = `status${state === "normal" ? "" : ` ${state}`}`;
}
function decodeReply(raw) {
    try {
        const reply = JSON.parse(raw);
        if (typeof reply !== "object" || reply === null) {
            throw new Error("The app returned an invalid response.");
        }
        return reply;
    }
    catch (error) {
        throw new Error(error instanceof Error ? error.message : "The app returned invalid data.");
    }
}
function invoke(call) {
    return new Promise((resolve, reject) => {
        call((raw) => {
            try {
                const reply = decodeReply(raw);
                if (reply.error) {
                    reject(new Error(reply.error));
                }
                else {
                    resolve(reply);
                }
            }
            catch (error) {
                reject(error);
            }
        });
    });
}
function tableData() {
    return snapshot?.tables.find((table) => table.name === selectedTable);
}
function updateSummary() {
    if (!snapshot)
        return;
    elements.path.textContent = snapshot.path;
    elements.path.title = snapshot.path;
    elements.size.textContent = DatabaseModel.formatSize(snapshot.size_bytes);
    elements.total.textContent = DatabaseModel.totalRecords(snapshot.tables).toLocaleString();
}
function renderTabs() {
    if (!snapshot)
        return;
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
function visibleRows(table) {
    const filtered = DatabaseModel.filterRows(table.rows, elements.filter.value);
    return DatabaseModel.sortRows(filtered, sortColumn, descending);
}
function renderRows() {
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
    const slice = DatabaseModel.paginate(matchingRows, page, Number(elements.pageSize.value));
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
            if (sortColumn === column)
                descending = !descending;
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
async function refresh() {
    if (loading)
        return;
    loading = true;
    elements.refresh.disabled = true;
    setStatus("Reading saved records...");
    try {
        const reply = await invoke((callback) => bridge.snapshot(callback));
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
    }
    catch (error) {
        setStatus(error instanceof Error ? error.message : "Could not read the database.", "error");
    }
    finally {
        loading = false;
        elements.refresh.disabled = false;
    }
}
async function backup() {
    elements.backup.disabled = true;
    setStatus("Preparing database backup...");
    try {
        const reply = await invoke((callback) => bridge.backup(callback));
        if (reply.cancelled) {
            setStatus("Backup cancelled.");
        }
        else if (reply.saved_to) {
            setStatus(`Backup saved to ${reply.saved_to}`, "success");
        }
        else {
            throw new Error("The app did not confirm the backup location.");
        }
    }
    catch (error) {
        setStatus(error instanceof Error ? error.message : "Could not back up the database.", "error");
    }
    finally {
        elements.backup.disabled = false;
    }
}
async function exportTable() {
    const table = tableData();
    if (!table)
        return;
    elements.export.disabled = true;
    setStatus(`Preparing ${table.name} CSV...`);
    try {
        const reply = await invoke((callback) => bridge.export_table(table.name, callback));
        if (reply.cancelled) {
            setStatus("Export cancelled.");
        }
        else if (reply.saved_to) {
            setStatus(`CSV saved to ${reply.saved_to}`, "success");
        }
        else {
            throw new Error("The app did not confirm the export location.");
        }
    }
    catch (error) {
        setStatus(error instanceof Error ? error.message : "Could not export the table.", "error");
    }
    finally {
        elements.export.disabled = table.count === 0;
    }
}
async function checkIntegrity() {
    elements.integrity.disabled = true;
    setStatus("Checking SQLite database integrity...");
    try {
        const reply = await invoke((callback) => bridge.check_integrity(callback));
        if (reply.integrity.length === 1 && reply.integrity[0] === "ok") {
            setStatus("SQLite integrity check passed.", "success");
        }
        else {
            setStatus(`SQLite reported: ${reply.integrity.join("; ")}`, "error");
        }
    }
    catch (error) {
        setStatus(error instanceof Error ? error.message : "Integrity check failed.", "error");
    }
    finally {
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
