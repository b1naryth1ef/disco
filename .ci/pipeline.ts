import {
  Job,
  pushStep,
  spawnChildJob,
} from "https://pkg.buildyboi.ci/buildy/core@0.0.7/mod.ts";
import * as Docker from "https://pkg.buildyboi.ci/buildy/docker@0.0.1/mod.ts";

export async function runTests(job: Job) {
  const version: string = job.args.version;

  const dockerFileTemplate = `
  FROM python:${version}-buster

  ADD requirements.txt .

  RUN pip install -r requirements.txt flake8
  `;

  const image = await Docker.buildImage({
    dockerfileContents: dockerFileTemplate,
    include: ["requirements.txt"],
  });

  pushStep("Tests");
  await Docker.run(`python setup.py test`, {
    image: image.id,
  });

  pushStep("Flake8");
  await Docker.run(`flake8 disco/`, {
    image: image.id,
  });
}

const versionMatrix = ["3.8", "3.7", "3.6"];

export async function run(job: Job) {
  for (const version of versionMatrix) {
    await spawnChildJob(`.ci/pipeline.ts:runTests`, {
      args: {
        version: version,
      },
      alias: `Test Python ${version}`,
    });
  }
}
