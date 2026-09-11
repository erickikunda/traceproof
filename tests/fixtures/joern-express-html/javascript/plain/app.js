import express from "express";
const app = express();
app.get("/hello", (incoming, response) => {
  response.type("text/plain").send(incoming.query.name);
});
