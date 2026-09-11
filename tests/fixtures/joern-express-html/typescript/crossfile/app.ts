import express from "express";
import { render } from "./view.ts";
const app = express();
app.get("/hello", (incoming, response) => {
  response.type("html").send(render(incoming.query.name));
});
