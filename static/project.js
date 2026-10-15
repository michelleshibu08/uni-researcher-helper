// The project workspace: sources, plan, writing space and reference list for one essay.
// Everything is saved as soon as it changes (see storage.js).

var STATUSES = [
  ["to_read", "To read"],
  ["read", "Read"],
  ["using", "Using"],
  ["not_using", "Not using"]
];
var sourceFilter = "all";

// ---------- Small helpers ----------

// Make an element with some text. Using textContent (not innerHTML) means
// nothing a student types can ever be run as code on the page.
function make(tag, text, className) {
  var element = document.createElement(tag);
  if (text) {
    element.textContent = text;
  }
  if (className) {
    element.className = className;
  }
  return element;
}

function button(text, onClick, className) {
  var element = make("button", text, className || "secondary small");
  element.type = "button";
  element.addEventListener("click", onClick);
  return element;
}

function current() {
  return activeProject(loadProjects());
}

function paperById(project, id) {
  return project.papers.filter(function (p) { return p.id === id; })[0];
}

// Papers marked "Not using" are left out of the reference list and citations.
function usedPapers(project) {
  return project.papers.filter(function (p) { return p.status !== "not_using"; });
}

// Most styles sort the list alphabetically. IEEE numbers papers in the order
// you cite them instead, so it keeps the order they were saved in.
function referenceList(project) {
  var style = project.style;
  var papers = usedPapers(project).filter(function (p) { return p[style]; });
  if (style !== "ieee") {
    papers.sort(function (a, b) { return a[style].localeCompare(b[style]); });
  }
  return papers.map(function (p, index) {
    return (style === "ieee" ? "[" + (index + 1) + "] " : "") + p[style];
  });
}

function downloadFile(url, body, filename) {
  fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  })
    .then(function (response) { return response.blob(); })
    .then(function (file) {
      var link = document.createElement("a");
      link.href = URL.createObjectURL(file);
      link.download = filename;
      link.click();
      URL.revokeObjectURL(link.href);
    });
}

// ---------- Choosing, creating and deleting projects ----------

function renderProjectBar() {
  var projects = loadProjects();
  var project = activeProject(projects);
  var select = document.getElementById("project-select");
  select.innerHTML = "";
  projects.forEach(function (p) {
    var option = make("option", p.name);
    option.value = p.id;
    option.selected = p.id === project.id;
    select.append(option);
  });
  document.getElementById("project-name").textContent = project.name;
  document.getElementById("question").value = project.question || "";
  document.getElementById("delete-project").hidden = projects.length < 2;
}

document.getElementById("project-select").addEventListener("change", function () {
  setActiveProject(this.value);
  renderAll();
});

document.getElementById("new-project").addEventListener("click", function () {
  var name = prompt("What's the new essay called?", "New essay");
  if (!name) {
    return;
  }
  var projects = loadProjects();
  var project = newProject(name.trim());
  projects.push(project);
  saveProjects(projects);
  setActiveProject(project.id);
  renderAll();
});

document.getElementById("rename-project").addEventListener("click", function () {
  var name = prompt("Rename this project", current().name);
  if (name) {
    updateActiveProject(function (p) { p.name = name.trim(); });
    renderAll();
  }
});

document.getElementById("delete-project").addEventListener("click", function () {
  var project = current();
  if (!confirm('Delete "' + project.name + '" and everything in it?')) {
    return;
  }
  var projects = loadProjects().filter(function (p) { return p.id !== project.id; });
  saveProjects(projects);
  setActiveProject(projects[0].id);
  renderAll();
});

document.getElementById("question").addEventListener("input", function () {
  var question = this.value;
  updateActiveProject(function (p) { p.question = question; });
});

document.getElementById("start-link").addEventListener("click", function (event) {
  // Take the student's question with them to the Get started page.
  var question = current().question;
  if (question) {
    event.preventDefault();
    window.location = URLS.start + "?question=" + encodeURIComponent(question);
  }
});

// ---------- 1. Sources ----------

function renderSources() {
  var project = current();
  var filters = document.getElementById("status-filters");
  filters.innerHTML = "";
  [["all", "All"]].concat(STATUSES).forEach(function (status) {
    var count = status[0] === "all"
      ? project.papers.length
      : project.papers.filter(function (p) { return p.status === status[0]; }).length;
    var chip = button(status[1] + " (" + count + ")", function () {
      sourceFilter = status[0];
      renderSources();
    }, "chip-button" + (sourceFilter === status[0] ? " active" : ""));
    filters.append(chip);
  });

  document.getElementById("no-sources").hidden = project.papers.length > 0;
  var list = document.getElementById("source-list");
  list.innerHTML = "";
  project.papers
    .filter(function (p) { return sourceFilter === "all" || p.status === sourceFilter; })
    .forEach(function (paper) {
      var card = make("article", "", "paper source");
      var title = make("h2");
      var link = make("a", paper.title || "Untitled paper");
      link.href = paper.url || "#";
      link.target = "_blank";
      title.append(link);
      card.append(title);
      card.append(make("p", [paper.authors, paper.year].filter(Boolean).join(" · "), "details"));

      // Reading status.
      var status = document.createElement("select");
      status.setAttribute("aria-label", "Reading status");
      STATUSES.forEach(function (s) {
        var option = make("option", s[1]);
        option.value = s[0];
        option.selected = paper.status === s[0];
        status.append(option);
      });
      status.addEventListener("change", function () {
        var value = status.value;
        updateActiveProject(function (p) { paperById(p, paper.id).status = value; });
        renderSources();
      });

      // Notes, saved as you type.
      var notes = make("textarea", "", "notes");
      notes.rows = 3;
      notes.placeholder = "Your notes: what does this paper find, and how will you use it?";
      notes.value = paper.notes || "";
      notes.addEventListener("input", function () {
        var value = notes.value;
        updateActiveProject(function (p) { paperById(p, paper.id).notes = value; });
      });

      var actions = make("div", "", "paper-actions");
      actions.append(status);
      var explore = make("a", "Explore related papers →");
      explore.href = URLS.explore.replace("PAPER_ID", paper.id);
      actions.append(explore);
      if (paper.hasAbstract !== false) {
        var check = make("a", "Check a claim →");
        check.href = URLS.check + "?paper_id=" + encodeURIComponent(paper.id);
        actions.append(check);
      }
      actions.append(button("Remove", function () {
        updateActiveProject(function (p) {
          p.papers = p.papers.filter(function (x) { return x.id !== paper.id; });
          p.plan.forEach(function (point) {
            point.paperIds = point.paperIds.filter(function (id) { return id !== paper.id; });
          });
        });
        renderAll();
      }));

      card.append(notes, actions);
      list.append(card);
    });
}

// ---------- 2. Plan ----------

function renderPlan() {
  var project = current();
  var list = document.getElementById("plan-list");
  list.innerHTML = "";
  if (!project.plan.length) {
    list.append(make("li", "No points yet. Add your first one below, e.g. \"Introduction: why sleep matters for teenagers\".", "details empty"));
  }
  project.plan.forEach(function (point, index) {
    var item = make("li", "", "plan-point");
    var text = make("textarea");
    text.rows = 2;
    text.placeholder = "What's this point or paragraph about?";
    text.value = point.text;
    text.addEventListener("input", function () {
      var value = text.value;
      updateActiveProject(function (p) { p.plan[index].text = value; });
    });

    // The papers attached to this point, shown as removable chips.
    var chips = make("div", "", "chips");
    point.paperIds.forEach(function (id) {
      var paper = paperById(project, id);
      if (!paper) {
        return;
      }
      var chip = make("span", (paper.intext_harvard || paper.title) + " ", "chip");
      chip.append(button("×", function () {
        updateActiveProject(function (p) {
          p.plan[index].paperIds = p.plan[index].paperIds.filter(function (x) { return x !== id; });
        });
        renderPlan();
      }, "chip-remove"));
      chips.append(chip);
    });

    var attach = document.createElement("select");
    attach.setAttribute("aria-label", "Attach a source");
    attach.append(make("option", project.papers.length ? "+ Attach a source…" : "Save papers to attach them"));
    project.papers.forEach(function (paper) {
      if (point.paperIds.indexOf(paper.id) === -1) {
        var option = make("option", paper.title);
        option.value = paper.id;
        attach.append(option);
      }
    });
    attach.addEventListener("change", function () {
      var id = attach.value;
      updateActiveProject(function (p) { p.plan[index].paperIds.push(id); });
      renderPlan();
    });

    var actions = make("div", "", "paper-actions");
    actions.append(attach);
    actions.append(button("↑", function () { movePoint(index, -1); }));
    actions.append(button("↓", function () { movePoint(index, 1); }));
    actions.append(button("Remove", function () {
      updateActiveProject(function (p) { p.plan.splice(index, 1); });
      renderPlan();
    }));

    item.append(text, chips, actions);
    list.append(item);
  });
}

function movePoint(index, step) {
  updateActiveProject(function (p) {
    var target = index + step;
    if (target < 0 || target >= p.plan.length) {
      return;
    }
    var moved = p.plan.splice(index, 1)[0];
    p.plan.splice(target, 0, moved);
  });
  renderPlan();
}

document.getElementById("add-point").addEventListener("click", function () {
  updateActiveProject(function (p) { p.plan.push({ text: "", paperIds: [] }); });
  renderPlan();
  var boxes = document.querySelectorAll("#plan-list textarea");
  if (boxes.length) {
    boxes[boxes.length - 1].focus();
  }
});

// ---------- 3. Write ----------

function countWords(text) {
  var words = text.trim().match(/\S+/g);
  return words ? words.length : 0;
}

function renderWordCount() {
  var project = current();
  var count = countWords(document.getElementById("draft").value);
  var target = parseInt(project.wordTarget, 10);
  var label = document.getElementById("word-count");
  label.textContent = target ? count + " / " + target : String(count);
  label.className = target && count > target * 1.1 ? "over" : "";
}

function renderWrite() {
  var project = current();
  document.getElementById("draft").value = project.draft || "";
  document.getElementById("word-target").value = project.wordTarget || "";
  var select = document.getElementById("cite-select");
  select.innerHTML = "";
  var style = project.style;
  var papers = usedPapers(project);
  if (!papers.length) {
    select.append(make("option", "Save papers to cite them"));
  }
  papers.forEach(function (paper) {
    // Styles without an in-text form (IEEE, Chicago, OSCOLA) fall back to Harvard's.
    var citation = paper["intext_" + style] || paper.intext_harvard;
    var option = make("option", citation + " " + paper.title.slice(0, 50));
    option.value = citation;
    select.append(option);
  });
  renderWordCount();
}

document.getElementById("draft").addEventListener("input", function () {
  var value = this.value;
  updateActiveProject(function (p) { p.draft = value; });
  renderWordCount();
});

document.getElementById("word-target").addEventListener("input", function () {
  var value = this.value;
  updateActiveProject(function (p) { p.wordTarget = value; });
  renderWordCount();
});

document.getElementById("insert-citation").addEventListener("click", function () {
  var citation = document.getElementById("cite-select").value;
  if (!citation || citation.charAt(0) !== "(") {
    return;
  }
  // Put the citation where the cursor is, with a space before it.
  var draft = document.getElementById("draft");
  var start = draft.selectionStart;
  var before = draft.value.slice(0, start);
  var insert = (before && !/\s$/.test(before) ? " " : "") + citation;
  draft.value = before + insert + draft.value.slice(draft.selectionEnd);
  draft.selectionStart = draft.selectionEnd = start + insert.length;
  draft.focus();
  draft.dispatchEvent(new Event("input"));
});

document.getElementById("download-essay").addEventListener("click", function () {
  var project = current();
  downloadFile(URLS.downloadEssay, {
    title: project.question || project.name,
    draft: project.draft || "",
    style: project.style,
    references: referenceList(project)
  }, "essay.docx");
});

document.getElementById("check-essay").addEventListener("click", function () {
  var project = current();
  var form = document.getElementById("check-form");
  form.elements.essay.value = project.draft || "";
  // The essay checker understands author-date styles, so send the Harvard list.
  form.elements.references.value = usedPapers(project).map(function (p) { return p.harvard; }).join("\n");
  form.submit();
});

// ---------- 4. References ----------

function renderReferences() {
  var project = current();
  document.getElementById("style").value = project.style;
  var list = document.getElementById("reference-list");
  list.innerHTML = "";
  var references = referenceList(project);
  if (!references.length) {
    list.append(make("li", "Save papers to build your reference list.", "details empty"));
  }
  references.forEach(function (reference) {
    list.append(make("li", reference));
  });
  var hidden = project.papers.length - usedPapers(project).length;
  document.getElementById("references-note").textContent = hidden
    ? hidden + " paper(s) marked \"Not using\" are left out."
    : "Every saved paper is included. Mark a paper \"Not using\" in Sources to leave it out.";
}

document.getElementById("style").addEventListener("change", function () {
  var value = this.value;
  updateActiveProject(function (p) { p.style = value; });
  renderReferences();
  renderWrite();
});

document.getElementById("copy-all").addEventListener("click", function () {
  navigator.clipboard.writeText(referenceList(current()).join("\n\n"));
  var copyButton = this;
  copyButton.textContent = "Copied";
  setTimeout(function () { copyButton.textContent = "Copy all"; }, 1500);
});

document.getElementById("download-references").addEventListener("click", function () {
  var project = current();
  downloadFile(URLS.downloadReferences, { style: project.style, references: referenceList(project) }, "reference-list.docx");
});

// ---------- Tabs ----------

function showTab(name) {
  document.querySelectorAll(".tab").forEach(function (tab) {
    tab.classList.toggle("active", tab.dataset.tab === name);
  });
  document.querySelectorAll(".tab-panel").forEach(function (panel) {
    panel.hidden = panel.id !== name;
  });
}

document.querySelectorAll(".tab").forEach(function (tab) {
  tab.addEventListener("click", function () {
    showTab(tab.dataset.tab);
    history.replaceState(null, "", "#" + tab.dataset.tab);
  });
});

function renderAll() {
  renderProjectBar();
  renderSources();
  renderPlan();
  renderWrite();
  renderReferences();
  updateProjectCount();
}

// Open the tab named in the address, e.g. /project#write, and follow later changes to it.
function showTabFromAddress() {
  var name = location.hash.slice(1);
  showTab(["sources", "plan", "write", "references"].indexOf(name) > -1 ? name : "sources");
}

renderAll();
showTabFromAddress();
// Redraw once the projects saved in the student's account have loaded.
document.addEventListener("projects-loaded", renderAll);
window.addEventListener("hashchange", showTabFromAddress);
