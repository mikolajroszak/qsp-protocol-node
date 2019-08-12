FROM mythril/myth@sha256:a4e01e358fc52517a1889fad415846876d27ad9e8f6555a59246b761a89ec882
RUN apt-get update && apt-get install -y curl &&  apt-get install -y apt-utils
RUN curl -sSL https://get.docker.com/ | sh