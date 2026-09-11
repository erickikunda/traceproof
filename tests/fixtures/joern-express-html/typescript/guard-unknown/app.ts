import express from "express";
const app = express();
app.get("/hello", (incoming, response) => {
  if (incoming.query.name.length < 30) response.type("html").send(incoming.query.name);
});
