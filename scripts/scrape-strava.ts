import { Stagehand } from "@browserbasehq/stagehand";
import { z } from "zod";
import StagehandConfig from "../stagehand.config.js";
import fs from "fs/promises";

// Define the Zod schemas for validation, based on the PRD.
const ActivitySchema = z.object({
  activityId: z.string(),
  sport: z.string().optional(),
  date: z.string().optional(),
  workoutName: z.string().optional(),
  duration: z.string().optional(),
  distance: z.string().optional(),
  elevation: z.string().optional(),
  relativeEffort: z.string().optional(),
  calories: z.string().optional(),
  averageHeartRate: z.string().optional(),
  maxHr: z.string().optional(),
  pace: z.string().optional(),
  weather: z.object({
    description: z.string().optional(),
    temperature: z.string().optional(),
    humidity: z.string().optional(),
    feelsLike: z.string().optional(),
    windSpeed: z.string().optional(),
    windDirection: z.string().optional(),
  }).optional(),
  laps: z.array(z.object({
    lapNumber: z.number().optional(),
    distance: z.string().optional(),
    time: z.string().optional(),
    pace: z.string().optional(),
    gap: z.string().optional(),
    elevation: z.string().optional(),
    heartRate: z.string().optional(),
  })).optional(),
});

export type Activity = z.infer<typeof ActivitySchema>;

const AllActivitiesSchema = z.object({
  activities: z.array(ActivitySchema),
});

// Function to read the last processed ID
async function getLastId(): Promise<string | null> {
  try {
    const data = await fs.readFile('data/last_id.json', 'utf-8');
    const json = JSON.parse(data);
    return json.last_id || null;
  } catch (error) {
    // If the file doesn't exist or is invalid, return null
    console.warn("Could not read last_id.json. Assuming no previous runs.");
    return null;
  }
}

async function scrapeStrava(activityUrlInput?: string) {
  let stagehand: Stagehand | null = null;
  console.log("Starting Strava scrape...");

  try {
    stagehand = new Stagehand(StagehandConfig);
    await stagehand.init();
    const page = stagehand.page;
    if (!page) throw new Error("Failed to get page from Stagehand.");

    let activities: Activity[] = [];

    if (activityUrlInput) {
      console.log(`Manual refresh requested for: ${activityUrlInput}`);
      const activityIdMatch = activityUrlInput.match(/activities\/(\d+)/);
      if (!activityIdMatch || !activityIdMatch[1]) {
        throw new Error(`Invalid Strava activity URL provided: ${activityUrlInput}`);
      }
      const activityId = activityIdMatch[1];
      activities.push({ activityId });
      console.log(`Processing single activity ID: ${activityId}`);
    } else {
      console.log("Navigating to Strava training page for nightly scrape...");
      await page.goto("https://www.strava.com/athlete/training");
      
      // Check if we are on the training page or the login page
      const onLoginPage = await page.evaluate(() => document.querySelector('a[href="/login"]') !== null);

      if (onLoginPage) {
        console.log("Session is not authenticated. Attempting direct login...");
        
        const email = process.env.STRAVA_EMAIL;
        const password = process.env.STRAVA_PASSWORD;

        if (!email || !password) {
          throw new Error("STRAVA_EMAIL and STRAVA_PASSWORD secrets must be set for fallback login.");
        }

        await page.goto("https://www.strava.com/login");

        await page.act({
          description: "Fill in the email address",
          selector: "#email",
          method: "fill",
          arguments: [email],
        });
        
        await page.act({
          description: "Fill in the password",
          selector: "#password",
          method: "fill",
          arguments: [password],
        });

        await page.act({
          description: "Click the login button",
          selector: "#login-button",
          method: "click",
        });

        // Wait for navigation to the dashboard, which confirms a successful login
        await page.waitForNavigation({ url: "**/dashboard" });
        console.log("Direct login successful. Navigating to training page.");
        
        // Navigate to the training page again after successful login
        await page.goto("https://www.strava.com/athlete/training");

      } else {
        console.log("Session is already authenticated via context.");
      }
      
      try {
        console.log("Waiting for the training log table to appear...");
        await page.waitForSelector("table.activities", { timeout: 30000 }); // Wait for 30 seconds
        console.log("Training log table found. Proceeding with scrape.");
      } catch (e) {
        throw new Error("Authentication failed. Waited for 30 seconds, but could not find the training log table. Please check credentials or website structure.");
      }

      const lastId = await getLastId();
      console.log(`Last processed activity ID: ${lastId}`);

      // This is the prompt that was used in the original director.ai script
      const extractionInstruction = "extract basic information for all activities shown on this page including the sport type, date, workout name, duration, distance, elevation, and relative effort. Also extract the URL for the workout name link.";

      console.log("Extracting basic activity data from training log...");
      const extractedData = await page.extract({
        instruction: extractionInstruction,
        schema: z.object({
          activities: z.array(z.object({
              sport: z.string().optional(),
              date: z.string().optional(),
              workoutName: z.string().optional(),
              duration: z.string().optional(),
              distance: z.string().optional(),
              elevation: z.string().optional(),
              relativeEffort: z.string().optional(),
              workoutUrl: z.string().url().optional(),
          })),
        }),
      });

      if (!extractedData.activities) {
          throw new Error("Could not extract activities from training page.");
      }
      
      console.log(`Found ${extractedData.activities.length} activities on the page.`);

      for (const item of extractedData.activities) {
          const activityIdMatch = item.workoutUrl?.match(/activities\/(\d+)/);
          if (activityIdMatch && activityIdMatch[1]) {
              const currentActivityId = activityIdMatch[1];
              
              if (currentActivityId === lastId) {
                  console.log(`Found last processed activity (${lastId}). Stopping scrape.`);
                  break;
              }

              activities.push({
                  activityId: currentActivityId,
                  ...item,
              });
          }
      }
    }

    if (activities.length === 0) {
        console.log("No new activities to process.");
        await fs.writeFile('activities.json', JSON.stringify([], null, 2));
    } else {
        console.log(`Found ${activities.length} new activities to process. Fetching details...`);

        // Sort activities by ID (newest first) for consistent processing order
        // Note: Strava IDs are sequential, so higher ID = newer activity
        const sortedActivities = activities.sort((a, b) => {
            const aId = parseInt(a.activityId);
            const bId = parseInt(b.activityId);
            return bId - aId; // Descending order (newest first)
        });

        for (let i = 0; i < sortedActivities.length; i++) {
            const activity = sortedActivities[i];
            console.log(`[${i+1}/${sortedActivities.length}] Fetching details for activity: ${activity.activityId}`);
            
            const activityUrl = `https://www.strava.com/activities/${activity.activityId}`;
            
            // Add retry logic for navigation and data extraction
            let success = false;
            let retryCount = 0;
            const maxRetries = 3;
            
            while (!success && retryCount < maxRetries) {
                try {
                    if (retryCount > 0) {
                        console.log(` -> Retry ${retryCount}/${maxRetries - 1} for activity ${activity.activityId}`);
                        // Wait a bit before retrying
                        await new Promise(resolve => setTimeout(resolve, 2000));
                    }

                    await page.goto(activityUrl, { timeout: 45000 }); // Increased timeout to 45 seconds

                    // Extract detailed info: weather, calories, HR, etc.
                    const detailedInfo = await page.extract({
                        instruction: "extract detailed information from this activity page including weather data (temperature, humidity, feels like, wind speed, wind direction), pace, calories, and any other performance metrics visible",
                        schema: z.object({
                            weather: z.object({
                                description: z.string().optional(),
                                temperature: z.string().optional(),
                                humidity: z.string().optional(),
                                feelsLike: z.string().optional(),
                                windSpeed: z.string().optional(),
                                windDirection: z.string().optional(),
                            }).optional(),
                            pace: z.string().optional(),
                            calories: z.string().optional(),
                            averageHeartRate: z.string().optional(),
                            maxHr: z.string().optional(), // Added maxHr
                        })
                    });

                    // Merge detailed info
                    activity.calories = detailedInfo.calories;
                    activity.averageHeartRate = detailedInfo.averageHeartRate;
                    activity.maxHr = detailedInfo.maxHr;
                    activity.weather = detailedInfo.weather;
                    activity.pace = detailedInfo.pace;
                    
                    // Go to laps tab and extract lap data
                    try {
                        // This selector now tries to find a link containing "Laps" OR "Segments"
                        const lapTabSelector = "xpath=//a[contains(text(), 'Laps') or contains(text(), 'Segments')]";
                        
                        await page.act({
                            description: "click the Laps or Segments tab",
                            method: "click",
                            selector: lapTabSelector
                        });

                        const lapData = await page.extract({
                            // The instruction is now more generic to handle all cases
                            instruction: "extract all lap, segment, or split data from the table, including number, distance, time, pace, GAP, elevation, and heart rate for each.",
                            schema: z.object({
                                laps: z.array(z.object({
                                    lapNumber: z.number().optional(),
                                    distance: z.string().optional(),
                                    time: z.string().optional(),
                                    pace: z.string().optional(),
                                    gap: z.string().optional(),
                                    elevation: z.string().optional(),
                                    heartRate: z.string().optional(),
                                })).optional(),
                            })
                        });
                        activity.laps = lapData.laps;
                        console.log(` -> Found ${lapData.laps?.length || 0} laps/segments.`);
                    } catch (e) {
                        console.warn(` -> Could not find or extract lap/segment data for activity ${activity.activityId}. Skipping.`);
                    }
                    
                    success = true; // If we get here, everything worked
                } catch (error) {
                    retryCount++;
                    console.error(` -> Error processing activity ${activity.activityId} (attempt ${retryCount}):`, error);
                    
                    if (retryCount >= maxRetries) {
                        console.error(` -> Failed to process activity ${activity.activityId} after ${maxRetries} attempts. Skipping.`);
                        // Don't fail the entire workflow, just skip this activity
                        break;
                    }
                }
            }
        }
        
        // Write the fully enriched data to the file
        await fs.writeFile('activities.json', JSON.stringify(sortedActivities, null, 2));
        console.log(`Successfully wrote ${sortedActivities.length} enriched activities to activities.json`);
    }

    console.log("Workflow completed successfully");
  } catch (error) {
    console.error("Workflow failed:", error);
    process.exit(1);
  } finally {
    if (stagehand) {
      console.log("Closing Stagehand connection.");
      await stagehand.close();
    }
  }
}

// Entry point to run the script
const activityUrl = process.argv[2]; // Get the URL from the command line
scrapeStrava(activityUrl).then(() => {
  console.log("Scrape script finished.");
  process.exit(0);
}); 