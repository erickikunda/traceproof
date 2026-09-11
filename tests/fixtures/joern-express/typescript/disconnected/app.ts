import express from "express";
const app = express();
const unused = (incoming, response) => {
  const term = incoming.query.code;
  response.send(eval(term));
};
