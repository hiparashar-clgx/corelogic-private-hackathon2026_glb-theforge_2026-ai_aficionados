@Library('CoreLogicDevopsUtils')
@Library('CoreLogicPipelineUtils')
@Library('CoreLogicOrgPipelineConfig')

import com.corelogic.devops.utils.PodTemplates

slaveTemplates = new PodTemplates()
def containerName = "python-uv"
def label = "${{GLOBAL:ORG_HYPHEN}}-${{GLOBAL:ECOSYSTEM}}-${containerName}"
def dImage = "us-docker.pkg.dev/clgx-artregistry-mgt-prd-3b27/idap-analytics-glb-genaifoundationglb-docker-local/${containerName}"



// Select the flow depending on branch
def flowName = 'featureFlow'
def branchName = env.BRANCH_NAME
println "We're at the branch $branchName"
if (branchName == "develop") {
    flowName = 'developFlow'
} else if (branchName == "master") {
    flowName = 'developFlow'
}


slaveTemplates.getPodTemplate(label, containerName, dImage) {
 node(label){
      container(containerName) {

	    def pipeline = pipelineManager.config()

        def buildType = new com.corelogic.pipeline.DeployableType(
            appName: '${{GLOBAL:APPLICATION_NAME_HYPHEN}}',
            ecosystemName: '${{GLOBAL:ECOSYSTEM}}',
            cloudNative: true,
            buildDockerImage: false,
            publishToArtifactRegistory: true,
            deployToFoundation: true,
            enableVeracodeForLibs: false,
            pipelineFlowName: flowName,
            fieldValueMap : [
                "Integration Tests": { runIntegrationTests() },
                "Unit Tests": { runUnitTests() }
            ],
            builder: new com.corelogic.builder.UvBuilder(
                preBuildStage: [
                    'Format Check': {
                        sh 'uv run --extra dev ruff format . --check'
                    },
                    'Lint Check': {
                        sh 'uv run --extra dev ruff check .'
                    },
                    'Type Check': {
                        sh 'uv run --extra dev mypy src/ tests/ examples/'
                    }
                ]
            ),
        )
        pipeline.execute(buildType)
        }
    }
}

def runUnitTests() {
    try {
        echo 'Running unit tests...'
        sh 'uv sync --all-packages --extra dev'
        sh 'uv run nox -s tests'
    } catch (e) {
        echo 'Unit Test Failures: ' + e.toString()
        throw e
    }
}

def runIntegrationTests() {
    try {
        echo 'Running integration tests...'
        sh 'uv sync --all-packages --extra dev'
        sh 'uv run nox -s integrations'
    } catch (e) {
        echo 'Integration Test Failures: ' + e.toString()
        throw e
    }
}
