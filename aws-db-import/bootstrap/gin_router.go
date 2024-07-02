package bootstrap

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/thegreatforge/sre-scripts/aws-db-import/pkg/middlewares"
)

// initialiseRouter initializes gin router
func (a *App) initialiseRouter() *gin.Engine {
	// To run gin in prod. mode
	gin.SetMode(gin.ReleaseMode)

	// To initialize gin engine
	r := gin.New()

	// Recovery middleware recovers from any panics and writes a 500 if there was one.
	r.Use(gin.Recovery())

	// Generate Request ID if not passed by the client
	r.Use(middlewares.GinRequestID())

	// Write access log
	r.Use(middlewares.GinLogger())

	// health check route
	r.GET("/health", middlewares.GinHealthHandler())

	// webpage handling
	r.LoadHTMLGlob("templates/*")
	r.GET("/", func(c *gin.Context) {
		c.HTML(http.StatusOK, "index.html", nil)
	})
	return r
}
