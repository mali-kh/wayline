FROM golang:1.23-alpine AS builder
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /data-agent ./cmd/data-agent

FROM alpine:3.20
COPY --from=builder /data-agent /data-agent
ENTRYPOINT ["/data-agent"]
