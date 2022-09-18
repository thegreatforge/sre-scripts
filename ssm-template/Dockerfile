FROM golang:1.18 as build-stage
ARG GOOS
WORKDIR /app
COPY go.mod ./
COPY go.sum ./
RUN go mod download
COPY *.go ./
RUN mkdir -p bin && cd bin && env GOOS=$GOOS go build -o ssm-template ../

FROM scratch as export-stage
COPY --from=build-stage /app/bin/ssm-template .