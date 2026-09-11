import express from "express";
const app = express();
app.get("/search", (incoming, response) => {
  const term = incoming.query.code;
  response.send(eval("1 + 1"));
});
