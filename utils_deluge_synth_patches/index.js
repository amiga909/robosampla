const fs = require("fs"),
  path = require("path");
const helpers = require("./xml-helpers");

const MIN_SAMPLE_LENGTH = 0; //3;
const DELETE_MIN_SAMPLE_SOURCE = false;
const DELUGE_SAMPLES_ROOT = "SAMPLES";

// Get processing folder and target folder from command line arguments
const PROCESSING_FOLDER = process.argv[2];
const TARGET_FOLDER = process.argv[3];

if (!PROCESSING_FOLDER || !TARGET_FOLDER) {
  console.error(
    "Error: Please provide both processing folder and target folder as arguments."
  );
  console.error("Usage: node index.js <processing_folder> <target_folder>");
  console.error("Example: node index.js CasioCZ230S MyDelugeKit");
  console.error("");
  console.error(
    "  processing_folder: Local folder containing sample subfolders"
  );
  console.error("  target_folder: Folder name to use in Deluge XML file paths");
  process.exit(1);
}

const XML_EXPORT_FOLDER = "XML";
const ROOT_FOLDER = __dirname;
const WORKING_DIR = __dirname + "/" + PROCESSING_FOLDER;

// Check if the processing folder exists
if (!fs.existsSync(WORKING_DIR)) {
  console.error(
    `Error: Processing folder "${PROCESSING_FOLDER}" does not exist in ${__dirname}`
  );
  console.error("Available folders:");
  const availableFolders = fs
    .readdirSync(__dirname, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => d.name)
    .filter((name) => !name.startsWith(".") && name !== "node_modules");
  availableFolders.forEach((folder) => console.error(`  - ${folder}`));
  process.exit(1);
}

console.log(`Processing samples from: ${PROCESSING_FOLDER}`);
console.log(`Target Deluge folder: ${TARGET_FOLDER}`);

// Create XML output directory if it doesn't exist
const XML_OUTPUT_DIR = path.join(__dirname, XML_EXPORT_FOLDER);
if (!fs.existsSync(XML_OUTPUT_DIR)) {
  fs.mkdirSync(XML_OUTPUT_DIR, { recursive: true });
  console.log(`Created XML output directory: ${XML_OUTPUT_DIR}`);
}

// Function to sanitize filename by replacing problematic characters
function sanitizeFilename(filename) {
  return filename;
}

const TEMPLATE = fs.readFileSync(__dirname + "/template.XML", "utf8");
const TEMPLATE_JSON = helpers.toJson(TEMPLATE);
const stats = {
  lengths: {},
};

let dirs = fs.readdirSync(WORKING_DIR, {
  withFileTypes: true,
});
dirs = dirs.filter((d) => {
  return d.isDirectory();
});

const WaveFile = require("wavefile").WaveFile;

dirs.forEach((wavFolder) => {
  console.log("wavFolder", wavFolder);
  let currentPath = WORKING_DIR + "/" + wavFolder.name;
  console.log("wavFolder path", currentPath);

  let wavs = fs.readdirSync(currentPath, {
    withFileTypes: true,
  });
  wavs = wavs.filter((w) => {
    return [".wav", ".aif", ".aiff"].includes(
      path.extname(w.name).toLowerCase()
    );
  });

  const ranges = [];
  const commonSubstring = common_substring(
    wavs.map((w) => {
      return w.name;
    })
  );

  let lengthRange = 0;
  wavs.forEach((wav) => {
    const buffer = fs.readFileSync(currentPath + "/" + wav.name);
    const waveFile = new WaveFile();
    waveFile.fromBuffer(buffer);
    const sampleLength = Math.floor(waveFile.chunkSize / 4); // - 10;
    lengthRange = Math.floor((sampleLength / 100000) * 2.5);
    const midiNo = helpers.getMidiNoFromFilenameLoopop(
      wav.name,
      commonSubstring
    );
    const payload = {
      sampleRange: {
        zone: {
          _startSamplePos: 0,
          _endSamplePos: sampleLength,
        },
        _rangeTopNote: midiNo, // omit if last
        _fileName: `${DELUGE_SAMPLES_ROOT}/${TARGET_FOLDER}/${wavFolder.name}/${wav.name}`,
        _transpose: 60 - midiNo,
        // _cents: '-44'
      },
    };
    ranges.push(payload);
  });

  ranges.sort((a, b) =>
    a._rangeTopNote > b._rangeTopNote
      ? 1
      : b._rangeTopNote > a._rangeTopNote
      ? -1
      : 0
  );

  const newXmlFile = TEMPLATE_JSON;
  newXmlFile.sound.osc1.sampleRanges = ranges;
  newXmlFile.sound.defaultParams.envelope1.release =
    helpers.getDelugeReleaseTime(wavFolder.name);

  stats.lengths[lengthRange] = stats.lengths[lengthRange]
    ? stats.lengths[lengthRange] + 1
    : 1;

  if (lengthRange > MIN_SAMPLE_LENGTH) {
    const sanitizedPatchName = sanitizeFilename(wavFolder.name);
    const xmlFileName = path.join(XML_OUTPUT_DIR, `${sanitizedPatchName}`);
    helpers.writeXmlFile(newXmlFile, xmlFileName);
    console.log(`Generated: ${sanitizedPatchName}.XML`);
  } else {
    if (DELETE_MIN_SAMPLE_SOURCE) {
      console.log("delete samples: ", currentPath);
      fs.rmdirSync(currentPath, { recursive: true });
    } else {
      console.log(`skipped ${wavFolder.name}, lengthRange: ${lengthRange}`);
    }
  }
});
console.log("stats", stats);

function common_substring(data) {
  var i,
    ch,
    memo,
    idx = 0;
  do {
    memo = null;
    for (i = 0; i < data.length; i++) {
      ch = data[i].charAt(idx);
      if (!ch) break;
      if (!memo) memo = ch;
      else if (ch != memo) break;
    }
  } while (i == data.length && idx < data.length && ++idx);
  return (data[0] || "").slice(0, idx);
}
