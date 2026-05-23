# Build from the repo root:
#   docker build -f cmd/ui-server/Dockerfile -t 192.168.1.163:5000/wl-ui-server:latest .
FROM node:20-alpine AS ui-builder
WORKDIR /ui
COPY ui/package.json ui/package-lock.json* ./
RUN npm install
COPY ui/ .
RUN npm run build

FROM golang:1.23-alpine AS go-builder
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /ui-server ./cmd/ui-server

FROM alpine:3.20
RUN apk add --no-cache ca-certificates
COPY --from=go-builder /ui-server /ui-server
COPY --from=ui-builder /ui/dist /ui/dist
ENV WL_UI_DIR=/ui/dist
ENV WL_DB_PATH=/data/wl-history.db
ENV WL_LISTEN_ADDR=:8080
ENTRYPOINT ["/ui-server"]
