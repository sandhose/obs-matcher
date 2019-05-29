node {
	def app1

	stage('Cleaning up working dir') {
		step([$class: 'WsCleanup'])
	}

	stage('Clone repository') {
		/* Let's make sure we have the repository cloned to our workspace */
		checkout scm
	}

	stage('web') {
		stage('Build image obs-matcher') {
			/* This builds the actual image; synonymous to
			* docker build on the command line */
			app1 = docker.build "dockerregistry.coe.int/councilofeurope/obs-matcher:latest"
		}
	}

	stage('Push image') {
		/* Finally, we'll push the image with two tags:
		* First, the incremental build number from Jenkins
		* Second, the 'latest' tag.
		* Pushing multiple tags is cheap, as all the layers are reused. */
		docker.withRegistry('https://dockerregistry.coe.int') {
			app1.push("latest")
		}
	}

	stage('Deploy On Docker Cluster') {
		/* This builds the actual image; synonymous to
		* docker build on the command line */
		sh 'DOCKER_HOST=tcp://olympus.coe.int:2375 docker stack deploy -c docker-compose.yml obs-matcher'
	}

}
