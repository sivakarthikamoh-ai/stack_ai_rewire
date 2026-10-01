# Helper Guide — AI-Native Model Serving (Assignment 1)

This is the "what do I actually do, in order" guide. Start by reviewing the problem description and workflow presented in Tiger OS, then download the complete assignment bundle. The generated `.claude/skills/ai-native-model-serving/SKILL.md` covers training the model
and writing the spec (Step 0-1) — everything after that is deliberately not scripted, and this
guide is what tells you how to approach it.


## What you should be able to do by the end of this assignment
- Direct an AI coding agent to build a production-shaped service from a spec you reviewed,
  and tell the difference between output you should accept and output you should push back on.
- Explain the reasoning behind at least one design decision in your spec you'd defend to a
  reviewer (an error-handling choice, a security-baseline call, a versioning scheme).
- Take a CI/CD pipeline from a feature branch through a build, a registry push, and a
  promotion to a second (QA) environment with a smoke test — the shape of a real deployment
  pipeline, not just "it built."
- Turn work you just did by hand into a reusable, concrete automation script (the skill-file
  update).

## Tiger OS, WSL, Claude Code, and Skill Setup

Before starting implementation, review the Tiger OS workflow and download the assignment bundle. The bundle contains the workflow, skill files, starter code, data, helper guide, and rubric.


Complete this setup inside WSL after Tiger OS has generated the workflow and skill files:

1. Open Ubuntu or the approved WSL Linux distribution.
2. Clone your Git repository into the WSL filesystem, for example under `~/projects/`.
3. Install or verify Python, Git, Docker access from WSL, and the project dependencies from `requirements.txt`.
4. Open Claude Code from the WSL project folder so it can read and update the same repository files.
5. Keep project-level Claude instructions in `CLAUDE.md` at the project root.
6. Add the Tiger OS bundle-provided skill files to the expected `.claude/skills/` folder structure.
7. Use the assignment skill from `.claude/skills/ai-native-model-serving/SKILL.md`.
8. Save screenshots, command logs, model artifacts, CI/CD evidence, and review notes in `outputs/artifacts/`.

## Prerequisites — do this first if you haven't already
This assignment assumes you're already comfortable with FastAPI basics and Docker
fundamentals. It is not teaching those from scratch. If you need to build that up first:
- [FastAPI: First Steps tutorial](https://fastapi.tiangolo.com/tutorial/first-steps/) through
  the request body / path & query parameters sections.
- [Docker: Get Started](https://docs.docker.com/get-started/) — enough to build, run, and tag
  an image, and to understand what a multi-stage build is.
- [Dockerfile best practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
  — worth a skim before Step 2 below, not just after something goes wrong.
- [GitLab CI/CD YAML syntax reference](https://docs.gitlab.com/ee/ci/yaml/), [GitLab CI/CD quickstart / pipeline basics](https://docs.gitlab.com/ee/ci/quick_start/) — GitLab CI/CD pipeline
- [Using CI/CD variables](https://docs.gitlab.com/ee/ci/variables/) — for $DOCKERHUB_USERNAME / $DOCKERHUB_TOKEN as masked/protected CI/CD variables
- [Docker Hub docs — Access tokens](https://docs.docker.com/security/for-developers/access-tokens/) — generating a scoped token instead of a password for $DOCKERHUB_TOKEN
- [Building Docker images with GitLab CI/CD](https://docs.gitlab.com/ee/ci/docker/using_docker_build.html) — the Docker-in-Docker build/push pattern
- [GitLab Environments and deployments guide](https://docs.gitlab.com/ee/ci/environments/) — QA promotion stage
- [FastAPI — Testing docs](https://fastapi.tiangolo.com/tutorial/testing/) — smoke-testing the container
- [pytest documentation](https://docs.pytest.org/en/stable/) — for Unit Testing


---

## 1. Kickoff — hand Claude the Tiger OS generated skill

In Claude Code, from the WSL project folder, either invoke the skill (e.g. `/ai-native-model-serving` if it's set up as a
slash command) or paste the full contents of `SKILL.md`, followed by something like:

```text
Use the instructions in .claude/skills/ai-native-model-serving/SKILL.md to complete Step 0 and Step 1 only.

Train the model using starter-code/src/train_model.py and the provided dataset. Produce model.joblib, model_card.md, and spec.md as described by the skill. Stop after Step 1 and summarize the decisions I need to review before you build the FastAPI service, Dockerfile, CI/CD pipeline, and tests.
```

Claude installs `requirements.txt` into your active venv, runs `train_model.py` to produce
`model.joblib` and `model_card.md` (Step 0), reads `model_card.md`, produces `spec.md` (Step
1), then stops and hands it back to you — the pause is built into the skill.

Read `spec.md`. If a decision it made isn't the one you'd make, for example a different error-handling approach, a different non-functional
requirement, a versioning scheme you'd rather use — say so and have Claude redo that part.
Otherwise, tell it to proceed. This is the last point where Claude is following a script —
everything after this, you direct it yourself, one request at a time.

---

## 2. Build it yourself — service, container, CI/CD (not scripted)

Use Claude Code from the WSL project folder to build. What needs to exist by the end of this section:
- **FastAPI service** (`app/main.py`, `app/schema.py`, etc.) implementing `/predict` and
  `/health` per your spec, with Pydantic validation against `model_card.md`'s ranges.
- **Dockerfile** — multi-stage, lean final stage, non-root user, pinned base image tag, with a
  `.dockerignore`.
- **`.gitlab-ci.yml`** — At minimum:
  `lint → unit test → contract test → integration test → build → push`. Use
  `$DOCKERHUB_USERNAME` / `$DOCKERHUB_TOKEN` to log in
  and push, tagged with `$CI_COMMIT_SHORT_SHA`.
- **A QA promotion stage** — this is the CD part of the pipeline. Add a second stage/job, gated on merge to a `qa` (or your default) branch, that pulls
  the image you just pushed and smoke-tests `/health` and `/predict` against it. GitLab CI's `environment:` keyword
   (`environment: name: qa`) gives you a visible promotion in
  GitLab's own Environments view.
- **Tests** (`tests/test_unit.py`, `tests/test_contract.py`, `tests/test_integration.py`) —
  ask Claude to include edge cases explicitly (malformed JSON, missing field, wrong type,
  out-of-range value, empty payload), and don't take the suite's word for it: deliberately
  weaken one piece of validation and confirm a test actually catches it before trusting the
  rest.
- **A self-review pass** — ask Claude to review its own diff for style/security issues once
  everything above exists, and resolve what it finds (fix or explicitly note why something's
  out of scope).

Smoke-test locally before you push anything:
```bash
docker build -t model-serving:local .
docker run -d -p 8000:8080 --name model-serving-local model-serving:local
curl http://localhost:8000/health
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"sqft": 1500, "bedrooms": 3, "bathrooms": 2.0, "age_years": 10, "location_score": 7.5}'
docker rm -f model-serving-local
```

---

## 3. Update the skill file

Now that you've built the service,
container, pipeline, tests, and done a self-review pass by hand, go back to
`.claude/skills/ai-native-model-serving/SKILL.md` and add to it — a Step 2
(wrapper/Dockerfile/CI-CD), a Step 3 (tests), a Step 4 (self-review and hand-off), written in
the same style as Step 0 and Step 1 already in the file: concrete, imperative, naming exact
files, exact checks, exact commands.

Ensure that given only your updated `.claude/skills/ai-native-model-serving/SKILL.md` and a
different model/dataset, it can follow it to a comparable result. If your new steps are too
specific to your exact choices, or too vague to act on, revise them before submitting.

---

## 4. Review and open the MR

Before pushing, do what you'd do for any merge request you're about to put your name on:
- Skim `spec.md` again against what actually got built — does the service do what you decided
  it should in Step 1?
- Confirm the QA promotion stage actually ran and smoke-tested successfully.
- Confirm your updated `.claude/skills/ai-native-model-serving/SKILL.md` is accurate to what you built.

```bash
git checkout -b assignment-1-model-serving
git add .
git commit -m "AI-native model serving: spec, service, CI/CD, tests, updated skill file"
git push -u origin assignment-1-model-serving
```
Open a **Merge Request** on GitLab. **Check the pipeline before requesting review** — if any
stage is red, fix it and push again.

Once green, request review and share the MR link with your reviewer.

---

## Quick pre-submission checklist
- [ ] `model.joblib` present and trained from the provided `data/house_prices.csv` (Claude's
      Step 0), not copied in from anywhere else
- [ ] `spec.md` reflects decisions you actually reviewed and would stand behind
- [ ] Service, Dockerfile, `.gitlab-ci.yml`, and tests built by you working with Claude, not by
      the skill
- [ ] `/health` and `/predict` smoke-tested locally against the built image
- [ ] Mutation check done by hand: a deliberately weakened validation was caught by a test
- [ ] Pipeline includes a real QA promotion stage (pull + smoke test), not just build-and-push
- [ ] `.claude/skills/ai-native-model-serving/SKILL.md` updated with concrete Step 2-4 content, accurate to what you actually built
- [ ] GitLab CI pipeline green (including QA stage) before requesting review
- [ ] Completed assignment zip submitted in Tiger Academy (LMS)
