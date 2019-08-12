FROM qspprotocol/securify@sha256:ad5637f7662aa80ca8c4716b7cb3a2999cdcb03d78daf71ba6ae13d982fd5b2b
RUN apt-get update && apt-get install -y curl &&  apt-get install -y apt-utils
RUN curl -sSL https://get.docker.com/ | sh

WORKDIR /
ENTRYPOINT ["java", "-Xmx16G", "-jar", "/securify_jar/securify.jar"]