const express = require("express");
const app = express();
app.get("/evaluate", (req, res) => {
    res.send(eval(req.query.expr));
});
