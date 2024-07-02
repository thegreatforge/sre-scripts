package bootstrap

import (
	"context"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/thegreatforge/gokit/logger"
	"github.com/thegreatforge/sre-scripts/aws-db-import/bootstrap/config"
	"github.com/thegreatforge/sre-scripts/aws-db-import/bootstrap/constants"
	"github.com/thegreatforge/sre-scripts/aws-db-import/pkg/middlewares"
)

type AppParams struct {
	ConfigPath string
}

type App struct {
	params AppParams
}

func NewApp(params AppParams) (*App, error) {
	app := new(App)
	app.params = params

	if params.ConfigPath == "" {
		params.ConfigPath = constants.DEFAULT_CONFIG_PATH
	}

	// init config
	configData, err := config.InitConfig(params.ConfigPath)
	if err != nil {
		return nil, err
	}

	// init logger
	if configData.Log.Mode == constants.CONFIG_LOG_MODE_DEV {
		err = logger.Initialize(
			logger.Formatter("console"),
			logger.Level("debug"),
		)
	} else {
		err = logger.Initialize()
	}
	if err != nil {
		return nil, err
	}
	return app, nil
}

func (a *App) Close() {
	logger.Info("shutting down app")
	logger.Sync()
}

func (a *App) Run() error {
	router := a.initialiseRouter()

	logger.Infof("starting server on host - %s port - %d", config.Data.Server.Host, config.Data.Server.Port)

	srv := &http.Server{
		Addr:    strings.Join([]string{config.Data.Server.Host, strconv.Itoa(config.Data.Server.Port)}, ":"),
		Handler: router,
	}

	go func() {
		// service connections
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Errorf("listen: %s\n", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	// kill (no param) default send syscall.SIGTERM
	// kill -2 is syscall.SIGINT
	// kill -9 is syscall.SIGKILL but can't be caught, so don't need to add it
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	logger.Info("marking server unhealthy")
	middlewares.GinMarkServerUnhealthy()

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := srv.Shutdown(ctx); err != nil {
		logger.WithError(err).Error("server forced to shutdown")
	}
	// catching ctx.Done(). timeout of 5 seconds.
	<-ctx.Done()
	return nil
}
