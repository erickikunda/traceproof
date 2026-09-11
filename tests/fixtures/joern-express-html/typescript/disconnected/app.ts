import express from "express";
const app = express();
app.get("/hello", (incoming, response) => {
  const unused = incoming.query.name;
  response.type("html").send("<p>constant</p>");
});
