const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");

const sourcePath = path.join(__dirname, "..", "web", "database-model.ts");
const source = fs.readFileSync(sourcePath, "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    target: ts.ScriptTarget.ES2020,
    module: ts.ModuleKind.None,
    strict: true,
  },
}).outputText;
const context = {};
vm.runInNewContext(compiled, context);
const model = context.DatabaseModel;

function test(name, callback) {
  try {
    callback();
    console.log(`PASS ${name}`);
  } catch (error) {
    console.error(`FAIL ${name}`);
    throw error;
  }
}

test("filters across visible columns without mutating input", () => {
  const rows = [
    { system: "Sol", species: "Stratum" },
    { system: "Achenar", species: "Bacterium" },
  ];
  const filtered = model.filterRows(rows, "STRAT");
  assert.equal(filtered.length, 1);
  assert.equal(filtered[0].species, "Stratum");
  assert.equal(rows.length, 2);
});

test("sorts numbers numerically and strings naturally", () => {
  const numeric = model.sortRows([{ n: 9 }, { n: 12 }, { n: 2 }], "n", false);
  assert.deepEqual(Array.from(numeric, (row) => row.n), [2, 9, 12]);
  const names = model.sortRows([{ name: "Sol 10" }, { name: "Sol 2" }], "name", false);
  assert.deepEqual(Array.from(names, (row) => row.name), ["Sol 2", "Sol 10"]);
});

test("pagination clamps page indexes and always has a usable page size", () => {
  const rows = Array.from({ length: 7 }, (_, index) => index);
  const last = model.paginate(rows, 99, 3);
  assert.equal(last.current, 2);
  assert.deepEqual(Array.from(last.items), [6]);
  const empty = model.paginate([], -1, 0);
  assert.equal(empty.count, 1);
  assert.deepEqual(Array.from(empty.items), []);
});

test("formats storage and combines table counts", () => {
  assert.equal(model.formatSize(null), "In-memory");
  assert.equal(model.formatSize(512), "512 bytes");
  assert.equal(model.formatSize(2048), "2.0 KB");
  assert.equal(model.formatSize(2 * 1024 * 1024), "2.00 MB");
  assert.equal(model.totalRecords([{ count: 4 }, { count: 7 }]), 11);
});

test("validates the database snapshot shape before rendering", () => {
  assert.equal(model.isValidSnapshot({
    path: "edbio.db",
    size_bytes: 20,
    tables: [{ name: "history", count: 0, rows: [] }],
  }), true);
  assert.equal(model.isValidSnapshot({ path: "edbio.db", tables: [] }), false);
  assert.equal(model.isValidSnapshot(null), false);
});
