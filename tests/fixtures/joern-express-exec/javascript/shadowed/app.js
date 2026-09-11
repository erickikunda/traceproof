import express from "express";
function exec(value) { return value; }
const app = express();
app.get("/run", (incoming, response) => {
  exec(incoming.query.command);
});
