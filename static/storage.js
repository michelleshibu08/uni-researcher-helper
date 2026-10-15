// Projects are kept in this browser's storage, so students don't need an account.
//
// A project looks like:
// { id, name, question, style, papers: [...], plan: [...], draft, wordTarget }
// and each saved paper has its references in every style, plus a status and notes.

var STORAGE_KEY = "projects";
var ACTIVE_KEY = "activeProject";

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
  updateProjectCount();
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
