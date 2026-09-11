import express from "express";
const app = express();
app.get("/hello", (incoming, response) => {
  response.type("html").send("<p>constant</p>");
});
