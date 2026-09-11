import express from "express";
import { render } from "./view.js";
const app = express();
app.get("/hello", (incoming, response) => {
  response.type("html").send(render(incoming.query.name));
});
