import serverless from "serverless-http";
import express, { Request, Response } from "express";
import cors from "cors";
import { shopRouter } from "../../webshop/src/api/shopRouter.js";
import { saasRouter } from "../../webshop/src/api/saasRouter.js";

const app = express();

app.use(cors());
app.use(express.json({ limit: "50mb" }));
app.use(express.urlencoded({ limit: "50mb", extended: true }));

// Health check endpoint
app.get("/api/health", (_req: Request, res: Response) => {
  res.json({ ok: true, status: "Netlify Function API Running", timestamp: new Date() });
});

// Route registration for both Netlify URL rewrites and direct function calls
app.use("/api/shop", shopRouter);
app.use("/api/saas", saasRouter);
app.use("/.netlify/functions/api/shop", shopRouter);
app.use("/.netlify/functions/api/saas", saasRouter);

export const handler = serverless(app);
