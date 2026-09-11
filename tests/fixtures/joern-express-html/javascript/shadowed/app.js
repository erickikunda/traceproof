import express from "express";
const other = { type(value) { return this; }, send(value) { return value; } };
const app = express();
app.get("/hello", (incoming, response) => {
  other.type("html").send(incoming.query.name);
});
