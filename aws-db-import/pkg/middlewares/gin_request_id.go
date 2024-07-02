package middlewares

import (
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/thegreatforge/gokit/logger"
)

const DefaultGinRequestIdKey string = "x-request-id"

func GinRequestID() gin.HandlerFunc {
	return func(c *gin.Context) {
		rid := c.GetHeader(DefaultGinRequestIdKey)

		if rid == "" {
			rid = uuid.New().String()
		}
		// Add request_id to request headers
		c.Request.Header.Set(DefaultGinRequestIdKey, rid)

		// add the service to logger context
		ctx := c.Request.Context()
		ctxWithLogger := logger.AppendFieldsToContext(ctx, logger.String(DefaultGinRequestIdKey, rid))
		c.Request = c.Request.WithContext(ctxWithLogger)
		c.Next()
	}
}
