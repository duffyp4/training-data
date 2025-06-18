import fs from 'fs/promises';
import { Activity } from './scrape-strava.js';

const INDEX_PATH = 'index.md';
const LAST_ID_PATH = 'data/last_id.json';
const ACTIVITIES_PATH = 'activities.json';

// --- UTILITY FUNCTIONS ---

/**
 * Reads the existing index.md and extracts all activity IDs from the JSON-LD blocks.
 */
async function getExistingIds(filePath: string): Promise<Set<string>> {
  try {
    const content = await fs.readFile(filePath, 'utf-8');
    const ids = new Set<string>();
    const regex = /"identifier": "(\d+)"/g;
    let match;
    while ((match = regex.exec(content)) !== null) {
      ids.add(match[1]);
    }
    console.log(`Found ${ids.size} existing activities in ${filePath}.`);
    return ids;
  } catch (error) {
    console.log("index.md not found. A new one will be created.");
    return new Set();
  }
}

/**
 * Updates the last_id.json file with the ID of the most recent activity.
 */
async function updateLastId(newestId: string) {
  await fs.writeFile(LAST_ID_PATH, JSON.stringify({ last_id: newestId }, null, 2));
  console.log(`Successfully updated last_id.json to: ${newestId}`);
}

/**
 * Converts an Activity object into a Markdown and JSON-LD string.
 */
function toMarkdown(act: Activity): string {
  // Dates need to be parsed to be re-formatted into ISO strings
  const startTime = act.date ? new Date(act.date).toISOString() : '';
  // A simple way to calculate endTime is to add duration to startTime
  // This is a simplification and might need a more robust solution
  let endTime = '';
  if (startTime && act.duration) {
      try {
        const durationParts = act.duration.split(':').map(Number);
        const durationMs = (durationParts[0] * 3600 + durationParts[1] * 60 + (durationParts[2] || 0)) * 1000;
        endTime = new Date(new Date(startTime).getTime() + durationMs).toISOString();
      } catch (e) {
          console.warn(`Could not parse duration '${act.duration}' to calculate end time.`);
      }
  }

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "ExerciseAction",
    "identifier": act.activityId,
    "exerciseType": act.sport || '',
    "startTime": startTime,
    "endTime": endTime,
    "distance": act.distance || '',
    "duration": act.duration || '',
    "elevationGain": act.elevation || '',
    "calories": act.calories || '',
    "averageHeartRate": act.averageHeartRate || '',
    "weather": act.weather || {},
    "laps": act.laps || [],
  };

  const md = `
### ${act.date} — ${act.workoutName} (${act.distance}, ${act.duration})

\`\`\`jsonld
${JSON.stringify(jsonLd, null, 2)}
\`\`\`
`;
  return md;
}

// --- MAIN LOGIC ---

async function renderFeed() {
  console.log("Starting feed render process...");

  // 1. Read the scraped activities
  let activities: Activity[];
  try {
    const activitiesJson = await fs.readFile(ACTIVITIES_PATH, 'utf-8');
    activities = JSON.parse(activitiesJson);
  } catch (error) {
    console.error("Error reading activities.json. Did the scrape script run correctly?", error);
    process.exit(1);
  }

  if (activities.length === 0) {
    console.log("No new activities to render. Exiting.");
    return;
  }

  console.log(`Processing ${activities.length} scraped activities.`);
  
  // 2. Get existing IDs to avoid duplicates
  const existingIds = await getExistingIds(INDEX_PATH);
  let existingContent = await fs.readFile(INDEX_PATH, 'utf-8').catch(() => '');
  
  // Separate new activities from activities that might be upgrades
  const newActivities = activities.filter(act => !existingIds.has(act.activityId));
  const potentialUpgrades = activities.filter(act => existingIds.has(act.activityId));

  // --- Handle Upgrades ---
  let upgradesCount = 0;
  for (const act of potentialUpgrades) {
    // An activity is an upgrade if it has weather or laps data now.
    const isUpgrade = act.weather || (act.laps && act.laps.length > 0);
    if (isUpgrade) {
      console.log(`Upgrading activity ${act.activityId} with full details.`);
      const newMarkdown = toMarkdown(act);
      // Regex to find the whole block for the specific activity ID
      const blockRegex = new RegExp(`### [\\s\\S]*?"identifier": "${act.activityId}"[\\s\\S]*?\`\`\`\n`);
      
      // Replace the old block with the new one
      existingContent = existingContent.replace(blockRegex, newMarkdown);
      upgradesCount++;
    }
  }
  if (upgradesCount > 0) {
    console.log(`Replaced ${upgradesCount} existing activities with enriched data.`);
  }

  // --- Handle New Activities ---
  if (newActivities.length === 0) {
    console.log("No new activities to add to the feed.");
  } else {
    console.log(`Found ${newActivities.length} new activities to prepend to the feed.`);
    
    const newContent = newActivities.map(toMarkdown).join('\\n');
    existingContent = newContent + existingContent;
    
    console.log(`Successfully prepended ${newActivities.length} activities to ${INDEX_PATH}.`);
  }
  
  // Write the final, potentially modified content back to the file
  await fs.writeFile(INDEX_PATH, existingContent);

  // 3. Update last_id.json with the newest activity ID from the scrape
  const newestActivity = activities.sort((a, b) => b.activityId.localeCompare(a.activityId))[0];
  if (newestActivity) {
      await updateLastId(newestActivity.activityId);
  }

  console.log("Feed render process completed.");
}


renderFeed().catch(error => {
  console.error("Failed to render feed:", error);
  process.exit(1);
}); 