import express from "express";
import { exec, execFile } from "child_process";
const app = express();
app.get("/run", (incoming, response) => {
  if (incoming.query.command.length < 30) exec(incoming.query.command);
});
