import express from "express";
import path from "path";
import cors from "cors";
import { shopRouter } from "./src/api/shopRouter.js";
import { saasRouter } from "./src/api/saasRouter.js";
import { autoMigrateDatabase } from "./src/db/index.js";

const app = express();
const PORT = parseInt(process.env.PORT || "3000", 10);

app.use(cors());
app.use(express.json({ limit: "50mb" }));
app.use(express.urlencoded({ limit: "50mb", extended: true }));

// Serve static assets from python app/static directory and webshop/public/static
const appStaticPath = path.join(process.cwd(), "app", "static");
const webshopStaticPath = path.join(process.cwd(), "webshop", "public", "static");

app.use("/static", express.static(appStaticPath));
app.use("/static", express.static(webshopStaticPath));

// Direct Express shop & saas routers
app.use("/api/shop", shopRouter);
app.use("/api/saas", saasRouter);

async function startServer() {
  // Test/migrate database connection asynchronously
  autoMigrateDatabase().catch((err) => console.error("[DB Boot Error]", err));

  if (process.env.NODE_ENV !== "production") {
    const { createServer } = await import("vite");
    const vite = await createServer({
      configFile: path.join(process.cwd(), "webshop", "vite.config.ts"),
      root: path.join(process.cwd(), "webshop"),
      server: { middlewareMode: true, port: 3000, host: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (_req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`WebShop server running on http://0.0.0.0:${PORT}`);
  });
}

startServer();
