namespace DatabaseModel {
  export type Row = Record<string, unknown>;

  export interface Page<RowType> {
    items: RowType[];
    current: number;
    count: number;
    firstIndex: number;
  }

  export function cellText(value: unknown): string {
    if (value === null || value === undefined) return "";
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
  }

  export function filterRows(rows: Row[], query: string): Row[] {
    const normalized = query.trim().toLocaleLowerCase();
    if (!normalized) return rows.slice();
    return rows.filter((row) =>
      Object.values(row).some((value) =>
        cellText(value).toLocaleLowerCase().includes(normalized)));
  }

  export function compareValues(left: unknown, right: unknown): number {
    if (typeof left === "number" && typeof right === "number") return left - right;
    return cellText(left).localeCompare(cellText(right), undefined, {
      numeric: true,
      sensitivity: "base",
    });
  }

  export function sortRows(rows: Row[], column: string, descending: boolean): Row[] {
    if (!column) return rows.slice();
    const sorted = rows.slice().sort((left, right) =>
      compareValues(left[column], right[column]));
    return descending ? sorted.reverse() : sorted;
  }

  export function paginate<RowType>(rows: RowType[], page: number, pageSize: number): Page<RowType> {
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

  export function formatSize(bytes: number | null): string {
    if (bytes === null) return "In-memory";
    if (bytes < 1024) return `${bytes} bytes`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  }

  export function totalRecords(tables: Array<{ count: number }>): number {
    return tables.reduce((sum, table) => sum + table.count, 0);
  }

  export function isValidSnapshot(value: unknown): value is {
    path: string;
    size_bytes: number | null;
    tables: Array<{ name: string; count: number; rows: Row[] }>;
  } {
    if (typeof value !== "object" || value === null) return false;
    const candidate = value as Record<string, unknown>;
    if (typeof candidate.path !== "string" || !Array.isArray(candidate.tables)) return false;
    if (candidate.size_bytes !== null && typeof candidate.size_bytes !== "number") return false;
    return candidate.tables.every((table) => {
      if (typeof table !== "object" || table === null) return false;
      const item = table as Record<string, unknown>;
      return typeof item.name === "string"
        && Number.isInteger(item.count)
        && Number(item.count) >= 0
        && Array.isArray(item.rows)
        && item.rows.every((row) => typeof row === "object" && row !== null);
    });
  }
}
