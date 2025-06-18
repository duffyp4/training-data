import Browserbase from "@browserbasehq/sdk";
import dotenv from "dotenv";

// Load environment variables from .env file
dotenv.config();

async function createContext() {
  const apiKey = process.env.BROWSERBASE_API_KEY;
  const projectId = process.env.BROWSERBASE_PROJECT_ID;

  if (!apiKey || !projectId) {
    console.error(
      "Error: BROWSERBASE_API_KEY and BROWSERBASE_PROJECT_ID must be set in your environment or a .env file."
    );
    process.exit(1);
  }

  console.log("Creating a new persistent Browserbase context...");

  try {
    const bb = new Browserbase({ apiKey });
    const context = await bb.contexts.create({
      projectId: projectId,
    });

    console.log("\\n✅ Success!\\n");
    console.log("Your new persistent Context ID is:");
    console.log(`-> ${context.id}\\n`);
    console.log("Save this ID. You will use it to take over the session for the initial login and set it as the STRAVA_CONTEXT_ID secret in your GitHub repository.");

  } catch (error) {
    console.error("\\n❌ Failed to create context:", error);
    process.exit(1);
  }
}

createContext(); 