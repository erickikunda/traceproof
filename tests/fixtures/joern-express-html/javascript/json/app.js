import express from "express";
const app = express();
app.get("/hello", (incoming, response) => {
  response.json({name: incoming.query.name});
});
