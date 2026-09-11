import express from "express";
import { run } from "./worker.js";
const app = express();
app.get("/run", (incoming, response) => {
  run(incoming.query.command);
});
