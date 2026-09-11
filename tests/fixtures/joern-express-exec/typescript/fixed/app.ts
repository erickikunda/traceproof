import express from "express";
import { exec, execFile } from "child_process";
const app = express();
app.get("/run", (incoming, response) => {
  exec("echo fixed");
});
