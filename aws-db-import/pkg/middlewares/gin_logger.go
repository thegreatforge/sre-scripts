package middlewares

import (
	"bytes"
	"io"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/thegreatforge/gokit/logger"
)

// GinLogger logs every request to stdout and allows changing log level per request
func GinLogger() gin.HandlerFunc {
	return func(c *gin.Context) {
		// read before calling further middlewares / handlers as
		// some evil middlewares modify this values
		path := c.Request.URL.Path
		query := c.Request.URL.RawQuery

		byteBody, _ := io.ReadAll(c.Request.Body)
		c.Request.Body = io.NopCloser(bytes.NewBuffer(byteBody))

		// Add request_id and other context fields
		ctx := c.Request.Context()
		l := logger.WithContextFields(ctx)

		start := time.Now()
		c.Next()
		end := time.Now()

		latency := end.Sub(start).Milliseconds()
		end = end.UTC()

		if len(c.Errors) > 0 {
			// Append error field if this is an erroneous request.
			for _, e := range c.Errors.Errors() {
				l.Error(e)
			}
		} else {

			accessLog := l.With(
				logger.Int("status", c.Writer.Status()),
				logger.String("method", c.Request.Method),
				logger.String("body_size", strconv.Itoa(len(byteBody))),
				logger.String("domain", c.Request.Host),
				logger.String("path", path),
				logger.String("query", query),
				logger.String("ip", c.ClientIP()),
				logger.String("user_agent", c.Request.UserAgent()),
				logger.String("time", end.Format(time.RFC3339)),
				logger.Int64("latency", latency),
			)

			if c.Writer.Status() >= 200 && c.Writer.Status() < 400 {
				accessLog.Info("access_log")
			} else {
				accessLog.With(
					logger.String("body", string(byteBody)),
				).Error("access_log")
			}
		}
	}
}
