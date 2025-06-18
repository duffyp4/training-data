import type { ConstructorParams } from "@browserbasehq/stagehand";
import dotenv from "dotenv";

dotenv.config();

const StagehandConfig: ConstructorParams = {
  verbose: 1,
  domSettleTimeoutMs: 30_000,
  modelName: "google/gemini-2.0-flash", // Using the specified google model
  modelClientOptions: {
    apiKey: process.env.GOOGLE_API_KEY,
  },
  
  // Using Browserbase environment for production runs
  env: "BROWSERBASE", 
  browserbaseConnectionOptions: {
    // The contextId will be loaded from environment variables
    // This allows for persistent sessions, avoiding repeated logins
    contextId: process.env.STRAVA_CONTEXT_ID,
  },
  
  // Persist the session data (cookies, local storage) for the given contextId
  persist: true, 
};

export default StagehandConfig; 