const express = require("express");
const app = express();
app.get("/evaluate", (req: any, res: any) => {
    res.send(JSON.stringify(req.query.expr));
});
