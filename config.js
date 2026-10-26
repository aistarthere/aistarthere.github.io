/*
  SERVICE PLACEHOLDERS. Fill these in once Donal has created the accounts (see ../stack.md).
  Leave a value as "" and the site shows a clearly-marked "coming soon" state instead of fake data.
*/
window.SITE_CONFIG = {
  // Tally form for idea suggestions (public form link, e.g. "https://tally.so/r/XXXXXX")
  tallySuggestFormUrl: "",
  // Tally form for upvotes. Needs a hidden field named "idea". The site appends ?idea=<id>
  tallyVoteFormUrl: "",
  // Google Sheet "counts" tab published to the web as CSV (File > Share > Publish to web > CSV).
  // Expected columns: idea,votes
  votesCsvUrl: "",
  // beehiiv embedded subscribe form: paste ONLY the src URL of the <script> beehiiv gives you
  beehiivEmbedScriptSrc: "https://subscribe-forms.beehiiv.com/v3/loader.js",
  // beehiiv form id (data-beehiiv-form attribute)
  beehiivFormId: "ab6909b5-473b-47b6-99c9-984f8ce6caa7",
  // Public link to the beehiiv publication (newsletter archive)
  beehiivPublicationUrl: "",
  // GoatCounter site code, e.g. "ai101hub" -> https://ai101hub.goatcounter.com
  goatcounterCode: "",
  // X (Twitter) handle for the hub (account created 2026-10-26).
  xHandle: "@aistarthere"
};
