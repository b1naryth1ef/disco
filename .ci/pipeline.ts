import {
  Job,
  pushStep,
  spawnChildJob,
} from "https://pkg.buildyboi.ci/buildy/core@0.0.7/mod.ts";
import * as Docker from "https://pkg.buildyboi.ci/buildy/docker@0.0.1/mod.ts";
import { readSecrets } from "https://pkg.buildyboi.ci/buildy/core@0.0.7/secrets.ts";

async function getImage(version: string): Promise<string> {
  const dockerFileTemplate = `
  FROM python:${version}-buster

  ADD requirements.txt .

  RUN pip install -r requirements.txt flake8 twine
  `;

  const image = await Docker.buildImage({
    dockerfileContents: dockerFileTemplate,
    include: ["requirements.txt"],
  });

  return image.id;
}

export async function runTests(job: Job) {
  const imageId = await getImage(job.args.version);

  pushStep("Tests");
  await Docker.run(`python setup.py test`, {
    image: imageId,
  });

  pushStep("Flake8");
  await Docker.run(`flake8 disco/`, {
    image: imageId,
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

export async function runRelease(job: Job) {
  const imageId = await getImage("3.8");

  const [twineUsername, twinePassword] = await readSecrets(
    "TWINE_USERNAME",
    "TWINE_PASSWORD"
  );

  await Docker.run(`python setup.py sdist`, {
    image: imageId,
  });

  await Docker.run(`python3 -m twine upload dist/*`, {
    image: imageId,
    env: [`TWINE_USERNAME=${twineUsername}`, `TWINE_PASSWORD=${twinePassword}`],
  });
}
