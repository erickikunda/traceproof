import express from "express";
const server = express();
server.post("/search", (payload, response) => {
  const term = payload.body.expression;
  response.send(eval(term));
});
