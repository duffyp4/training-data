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
  let startTime = '';
  if (act.date) {
    try {
      // Try parsing the date directly first
      let parsedDate = new Date(act.date);
      // If that fails (Invalid Date), try some common formats
      if (isNaN(parsedDate.getTime())) {
        // Handle format like "December 30, 2024 at 6:40 AM"
        const dateStr = act.date.replace(' at ', ' ');
        parsedDate = new Date(dateStr);
      }
      startTime = isNaN(parsedDate.getTime()) ? '' : parsedDate.toISOString();
    } catch (e) {
      console.warn(`Could not parse date '${act.date}'. Using empty string.`);
      startTime = '';
    }
  }
  
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
    "pace": act.pace || '',
    "calories": act.calories || '',
    "averageHeartRate": act.averageHeartRate || '',
    "weather": act.weather || {},
    "laps": act.laps || [],
  };

  const md = `
### ${act.date} — ${act.workoutName} (${act.distance}, ${act.duration}${act.pace ? `, ${act.pace}` : ''})

\`\`\`jsonld
${JSON.stringify(jsonLd, null, 2)}
\`\`\`
`;
  return md;
}

/**
 * Ensures the entire index.md file is sorted by activity ID (newest first)
 * This fixes any ordering issues from previous processing
 */
async function ensureProperSorting(filePath: string) {
  try {
    const content = await fs.readFile(filePath, 'utf-8');
    
    // Split content into individual activity blocks
    const activityBlocks = content.split(/(?=### )/).filter(block => block.trim());
    
    // Find header content (everything before the first activity)
    const headerMatch = content.match(/^([\s\S]*?)(?=### )/);
    const header = headerMatch ? headerMatch[1] : '';
    
    // Extract activity IDs and sort blocks
    const blocksWithIds = activityBlocks
      .map(block => {
        const idMatch = block.match(/"identifier": "(\d+)"/);
        return {
          block: block,
          id: idMatch ? parseInt(idMatch[1]) : 0
        };
      })
      .filter(item => item.id > 0) // Only keep blocks with valid IDs
      .sort((a, b) => b.id - a.id); // Sort by ID descending (newest first)
    
    // Reconstruct the file
    const sortedContent = header + blocksWithIds.map(item => item.block).join('');
    
    await fs.writeFile(filePath, sortedContent);
    console.log(`Ensured ${blocksWithIds.length} activities are properly sorted by ID (newest first).`);
    
  } catch (error) {
    console.warn("Could not sort index.md file:", error);
  }
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
    
    // Sort new activities by ID (newest first) to ensure proper order
    const sortedNewActivities = newActivities.sort((a, b) => {
      const aId = parseInt(a.activityId);
      const bId = parseInt(b.activityId);
      return bId - aId; // Descending order (newest first)
    });
    
    const newContent = sortedNewActivities.map(toMarkdown).join('\\n');
    existingContent = newContent + existingContent;
    
    console.log(`Successfully prepended ${newActivities.length} activities to ${INDEX_PATH}.`);
  }
  
  // Write the final, potentially modified content back to the file
  await fs.writeFile(INDEX_PATH, existingContent);

  // 3. Update last_id.json with the newest activity ID from the scrape (using numeric comparison)
  const newestActivity = activities.sort((a, b) => {
    const aId = parseInt(a.activityId);
    const bId = parseInt(b.activityId);
    return bId - aId; // Descending order (newest first)
  })[0];
  
  if (newestActivity) {
      await updateLastId(newestActivity.activityId);
  }

  // 4. Ensure the entire index.md file is properly sorted (fixes any legacy ordering issues)
  await ensureProperSorting(INDEX_PATH);

  console.log("Feed render process completed.");
}


renderFeed().catch(error => {
  console.error("Failed to render feed:", error);
  process.exit(1);
}); 