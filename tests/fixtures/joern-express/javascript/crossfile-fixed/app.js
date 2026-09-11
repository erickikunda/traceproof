import { dispatch } from "./service.js";
import express from "express";
const app = express();
app.get("/search", (incoming, response) => {
  const term = incoming.params.expression;
  response.send(dispatch(term));
});
