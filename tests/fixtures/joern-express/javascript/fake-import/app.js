import express from "other";
const app = express();
app.get("/search", (incoming, response) => {
  const term = incoming.query.code;
  response.send(eval(term));
});
