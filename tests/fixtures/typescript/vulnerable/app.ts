const express = require("express");
const app = express();
app.get("/evaluate", (req: any, res: any) => {
    res.send(eval(req.query.expr));
});
