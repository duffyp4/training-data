import type { ConstructorParams } from "@browserbasehq/stagehand";
import dotenv from "dotenv";

dotenv.config();

// Ensure required environment variables are set
if (!process.env.STRAVA_CONTEXT_ID || !process.env.BROWSERBASE_PROJECT_ID) {
  throw new Error("Required environment variables (STRAVA_CONTEXT_ID, BROWSERBASE_PROJECT_ID) are not set.");
}

const StagehandConfig: ConstructorParams = {
  verbose: 1,
  domSettleTimeoutMs: 45_000, // Increased to 45 seconds
  modelName: "google/gemini-2.0-flash", // Using the specified google model
  modelClientOptions: {
    apiKey: process.env.GOOGLE_API_KEY,
  },
  
  // Using Browserbase environment for production runs
  env: "BROWSERBASE", 
  
  // This is the correct way to pass parameters to the underlying Browserbase session
  // for context persistence when using the Stagehand SDK.
  browserbaseSessionCreateParams: {
    projectId: process.env.BROWSERBASE_PROJECT_ID,
    browserSettings: {
      context: {
        id: process.env.STRAVA_CONTEXT_ID,
        persist: true,
      },
    },
  },
};

export default StagehandConfig; 