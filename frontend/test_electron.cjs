const e = require("electron");
console.log("type:", typeof e);
if (typeof e === "object") {
  console.log("keys:", Object.keys(e).join(", "));
  console.log("has protocol:", "protocol" in e);
}
