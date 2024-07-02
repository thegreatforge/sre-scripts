package middlewares

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

var ginHealthStatus string = "healthy"

func GinHealthHandler() gin.HandlerFunc {
	return func(c *gin.Context) {
		if ginHealthStatus != "healthy" {
			c.JSON(http.StatusServiceUnavailable, "unhealthy")
			return
		}
		c.JSON(http.StatusOK, "healthy")
	}
}

func GinMarkServerUnhealthy() {
	ginHealthStatus = "unhealthy"
}
