// Projects are kept in this browser's storage so pages load instantly. When a student
// is logged in, every change is also saved to their account on the server, and their
// saved projects are loaded from the server when a page opens.
//
// A project looks like:
// { id, name, question, style, papers: [...], plan: [...], draft, wordTarget }
// and each saved paper has its references in every style, plus a status and notes.

var STORAGE_KEY = "projects";
var ACTIVE_KEY = "activeProject";
// Whose projects the browser copy belongs to: a user ID, or "guest".
var OWNER_KEY = "projectsOwner";

var page = document.body.dataset;
var LOGGED_IN = page.loggedIn === "yes";
var OWNER = LOGGED_IN ? page.userId : "guest";

function readStorage(key, fallback) {
  try {
    var value = localStorage.getItem(key);
    return value === null ? fallback : JSON.parse(value);
  } catch (error) {
    return fallback;
  }
}

function writeStorage(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (error) {
    // Storage can be blocked (for example in private browsing); the change just won't be kept.
  }
}

function newProject(name) {
  return {
    id: "p" + Date.now(),
    name: name || "My essay",
    question: "",
    style: "harvard",
    papers: [],
    plan: [],
    draft: "",
    wordTarget: ""
  };
}

function loadProjects() {
  // Never show one person's projects to someone else using the same browser.
  // (Projects made as a guest are kept, so they can move into a new account.)
  var owner = readStorage(OWNER_KEY, "guest");
  if (owner !== "guest" && owner !== OWNER) {
    writeStorage(STORAGE_KEY, null);
    writeStorage(OWNER_KEY, OWNER);
  }
  var projects = readStorage(STORAGE_KEY, null);
  if (!projects || !projects.length) {
    // Papers saved before projects existed move into a first project.
    var project = newProject("My essay");
    project.papers = readStorage("savedPapers", []).map(function (paper) {
      paper.status = paper.status || "to_read";
      paper.notes = paper.notes || "";
      return paper;
    });
    projects = [project];
    writeStorage(STORAGE_KEY, projects);
  }
  return projects;
}

function saveProjects(projects) {
  writeStorage(STORAGE_KEY, projects);
  // A logged-in user's projects only become theirs once the account has loaded,
  // so a brand-new account can still pick up the guest projects.
  if (!LOGGED_IN || accountLoaded) {
    writeStorage(OWNER_KEY, OWNER);
  }
  updateProjectCount();
  if (LOGGED_IN) {
    saveToAccountSoon(projects);
  }
}

// Typing saves on every key press, so wait until the student pauses for a second
// before sending the projects to the server, instead of sending hundreds of requests.
var saveTimer = null;
var accountLoaded = false;
function saveToAccountSoon(projects) {
  if (!accountLoaded) {
    // Don't overwrite the account before we've seen what's in it.
    return;
  }
  clearTimeout(saveTimer);
  saveTimer = setTimeout(function () {
    fetch(page.projectsUrl, {
      method: "PUT",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": page.csrf },
      body: JSON.stringify(projects)
    });
  }, 1000);
}

// When a logged-in page opens, fetch the projects saved in the account.
function loadFromAccount() {
  if (!LOGGED_IN) {
    return;
  }
  // Remember what this browser had before, in case the account is brand new.
  var guestProjects = readStorage(OWNER_KEY, "guest") === "guest" ? readStorage(STORAGE_KEY, null) : null;
  fetch(page.projectsUrl)
    .then(function (response) { return response.json(); })
    .then(function (data) {
      accountLoaded = true;
      if (data.projects && data.projects.length) {
        writeStorage(STORAGE_KEY, data.projects);
        writeStorage(OWNER_KEY, OWNER);
      } else if (guestProjects && guestProjects.length) {
        // A new account keeps the projects the student made before signing up.
        writeStorage(STORAGE_KEY, guestProjects);
        writeStorage(OWNER_KEY, OWNER);
        saveToAccountSoon(guestProjects);
      }
      updateProjectCount();
      // Let the page redraw with the account's projects.
      document.dispatchEvent(new Event("projects-loaded"));
    });
}

function activeProject(projects) {
  var id = readStorage(ACTIVE_KEY, null);
  var found = projects.filter(function (p) { return p.id === id; })[0];
  return found || projects[0];
}

function setActiveProject(id) {
  writeStorage(ACTIVE_KEY, id);
}

// Run a change on the active project and save it straight away.
function updateActiveProject(change) {
  var projects = loadProjects();
  var project = activeProject(projects);
  change(project);
  saveProjects(projects);
  return project;
}

function updateProjectCount() {
  var counter = document.getElementById("saved-count");
  if (counter) {
    counter.textContent = activeProject(loadProjects()).papers.length;
  }
}

// Logging out clears this browser's copy, so the next person can't see it.
document.addEventListener("submit", function (event) {
  if (event.target.classList.contains("nav-form")) {
    writeStorage(STORAGE_KEY, null);
    writeStorage(OWNER_KEY, "guest");
  }
});
