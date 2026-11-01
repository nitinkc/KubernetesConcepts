# orders — Go, multi-stage. Run as non-root.
FROM golang:1.22-alpine AS build
WORKDIR /src
COPY go.mod go.sum* ./
RUN go mod download
COPY main.go .
RUN CGO_ENABLED=0 go build -o /orders .

FROM alpine:3.20
RUN adduser -D -u 10001 app
USER 10001
COPY --from=build /orders /orders
EXPOSE 8080
ENTRYPOINT ["/orders"]
