"""Dashboard manager for creating and managing BI dashboards."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from dataforge_common.logging import get_logger

logger = get_logger(__name__)


class DashboardStatus(str, Enum):
    """Dashboard status."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class VisualizationType(str, Enum):
    """Visualization types."""

    LINE_CHART = "line_chart"
    BAR_CHART = "bar_chart"
    PIE_CHART = "pie_chart"
    SCATTER_PLOT = "scatter_plot"
    TABLE = "table"
    METRIC = "metric"
    HEATMAP = "heatmap"
    AREA_CHART = "area_chart"
    FUNNEL = "funnel"
    GAUGE = "gauge"


@dataclass
class DataSource:
    """Data source configuration."""

    source_id: str
    name: str
    type: str  # database, api, file
    connection_string: Optional[str] = None
    query: Optional[str] = None
    file_path: Optional[str] = None
    api_endpoint: Optional[str] = None
    refresh_interval: int = 300  # seconds
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Visualization:
    """Visualization configuration."""

    viz_id: str
    name: str
    type: VisualizationType
    data_source_id: str
    config: Dict[str, Any]
    position: Dict[str, int]  # x, y, width, height
    filters: List[Dict[str, Any]] = field(default_factory=list)
    refresh_on_load: bool = True


@dataclass
class Dashboard:
    """Dashboard definition."""

    dashboard_id: str
    name: str
    description: str
    owner: str
    status: DashboardStatus = DashboardStatus.DRAFT
    visualizations: List[Visualization] = field(default_factory=list)
    data_sources: List[DataSource] = field(default_factory=list)
    layout: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = None
    access_control: Dict[str, List[str]] = field(default_factory=dict)
    settings: Dict[str, Any] = field(default_factory=dict)


class DashboardManager:
    """
    Dashboard manager for BI dashboards.

    Provides:
    - Dashboard creation and management
    - Visualization configuration
    - Data source management
    - Publishing and sharing
    - Access control

    Example:
        manager = DashboardManager()

        # Create dashboard
        dashboard = manager.create_dashboard(
            name="Sales Dashboard",
            description="Monthly sales overview",
            owner="analytics_team"
        )

        # Add data source
        manager.add_data_source(
            dashboard_id=dashboard.dashboard_id,
            source_id="sales_db",
            name="Sales Database",
            type="database",
            connection_string="postgresql://...",
            query="SELECT * FROM sales WHERE date >= CURRENT_DATE - 30"
        )

        # Add visualization
        manager.add_visualization(
            dashboard_id=dashboard.dashboard_id,
            viz_id="revenue_chart",
            name="Monthly Revenue",
            type=VisualizationType.LINE_CHART,
            data_source_id="sales_db",
            config={
                "x_axis": "date",
                "y_axis": "revenue",
                "title": "Monthly Revenue Trend"
            }
        )

        # Publish dashboard
        manager.publish_dashboard(dashboard.dashboard_id)
    """

    def __init__(self, storage_backend: str = "memory"):
        """
        Initialize dashboard manager.

        Args:
            storage_backend: Storage backend (memory, database)
        """
        self.storage_backend = storage_backend
        self.logger = logger

        # In-memory storage
        self.dashboards: Dict[str, Dashboard] = {}

        self.logger.info("Dashboard manager initialized", backend=storage_backend)

    def create_dashboard(
        self,
        name: str,
        description: str,
        owner: str,
        tags: Optional[List[str]] = None,
    ) -> Dashboard:
        """
        Create new dashboard.

        Args:
            name: Dashboard name
            description: Dashboard description
            owner: Dashboard owner
            tags: Tags for categorization

        Returns:
            Created dashboard
        """
        dashboard_id = f"dashboard_{len(self.dashboards) + 1}_{datetime.utcnow().timestamp()}"

        dashboard = Dashboard(
            dashboard_id=dashboard_id,
            name=name,
            description=description,
            owner=owner,
            tags=tags or [],
            access_control={"viewers": [], "editors": [owner]},
        )

        self.dashboards[dashboard_id] = dashboard

        self.logger.info("Dashboard created", dashboard_id=dashboard_id, owner=owner)

        return dashboard

    def get_dashboard(self, dashboard_id: str) -> Dashboard:
        """Get dashboard by ID."""
        if dashboard_id not in self.dashboards:
            raise ValueError(f"Dashboard not found: {dashboard_id}")

        return self.dashboards[dashboard_id]

    def list_dashboards(
        self,
        owner: Optional[str] = None,
        tags: Optional[List[str]] = None,
        status: Optional[DashboardStatus] = None,
    ) -> List[Dashboard]:
        """
        List dashboards with filters.

        Args:
            owner: Filter by owner
            tags: Filter by tags
            status: Filter by status

        Returns:
            List of dashboards
        """
        results = list(self.dashboards.values())

        if owner:
            results = [d for d in results if d.owner == owner]

        if tags:
            results = [d for d in results if any(t in d.tags for t in tags)]

        if status:
            results = [d for d in results if d.status == status]

        return results

    def add_data_source(
        self,
        dashboard_id: str,
        source_id: str,
        name: str,
        type: str,
        **kwargs,
    ) -> None:
        """
        Add data source to dashboard.

        Args:
            dashboard_id: Dashboard identifier
            source_id: Data source identifier
            name: Data source name
            type: Data source type
            **kwargs: Additional data source parameters
        """
        dashboard = self.get_dashboard(dashboard_id)

        data_source = DataSource(
            source_id=source_id,
            name=name,
            type=type,
            **kwargs,
        )

        dashboard.data_sources.append(data_source)
        dashboard.updated_at = datetime.utcnow()

        self.logger.info(
            "Data source added",
            dashboard_id=dashboard_id,
            source_id=source_id,
        )

    def add_visualization(
        self,
        dashboard_id: str,
        viz_id: str,
        name: str,
        type: VisualizationType,
        data_source_id: str,
        config: Dict[str, Any],
        position: Optional[Dict[str, int]] = None,
    ) -> None:
        """
        Add visualization to dashboard.

        Args:
            dashboard_id: Dashboard identifier
            viz_id: Visualization identifier
            name: Visualization name
            type: Visualization type
            data_source_id: Data source identifier
            config: Visualization configuration
            position: Position and size (x, y, width, height)
        """
        dashboard = self.get_dashboard(dashboard_id)

        # Verify data source exists
        if not any(ds.source_id == data_source_id for ds in dashboard.data_sources):
            raise ValueError(f"Data source not found: {data_source_id}")

        # Auto-position if not specified
        if position is None:
            num_viz = len(dashboard.visualizations)
            position = {
                "x": (num_viz % 2) * 6,
                "y": (num_viz // 2) * 4,
                "width": 6,
                "height": 4,
            }

        visualization = Visualization(
            viz_id=viz_id,
            name=name,
            type=type,
            data_source_id=data_source_id,
            config=config,
            position=position,
        )

        dashboard.visualizations.append(visualization)
        dashboard.updated_at = datetime.utcnow()

        self.logger.info(
            "Visualization added",
            dashboard_id=dashboard_id,
            viz_id=viz_id,
            type=type.value,
        )

    def update_visualization(
        self,
        dashboard_id: str,
        viz_id: str,
        config: Optional[Dict[str, Any]] = None,
        position: Optional[Dict[str, int]] = None,
    ) -> None:
        """Update visualization configuration."""
        dashboard = self.get_dashboard(dashboard_id)

        for viz in dashboard.visualizations:
            if viz.viz_id == viz_id:
                if config:
                    viz.config.update(config)
                if position:
                    viz.position = position

                dashboard.updated_at = datetime.utcnow()

                self.logger.info(
                    "Visualization updated",
                    dashboard_id=dashboard_id,
                    viz_id=viz_id,
                )
                return

        raise ValueError(f"Visualization not found: {viz_id}")

    def remove_visualization(self, dashboard_id: str, viz_id: str) -> None:
        """Remove visualization from dashboard."""
        dashboard = self.get_dashboard(dashboard_id)

        dashboard.visualizations = [
            v for v in dashboard.visualizations if v.viz_id != viz_id
        ]
        dashboard.updated_at = datetime.utcnow()

        self.logger.info(
            "Visualization removed",
            dashboard_id=dashboard_id,
            viz_id=viz_id,
        )

    def publish_dashboard(self, dashboard_id: str) -> None:
        """Publish dashboard."""
        dashboard = self.get_dashboard(dashboard_id)

        dashboard.status = DashboardStatus.PUBLISHED
        dashboard.published_at = datetime.utcnow()
        dashboard.updated_at = datetime.utcnow()

        self.logger.info("Dashboard published", dashboard_id=dashboard_id)

    def archive_dashboard(self, dashboard_id: str) -> None:
        """Archive dashboard."""
        dashboard = self.get_dashboard(dashboard_id)

        dashboard.status = DashboardStatus.ARCHIVED
        dashboard.updated_at = datetime.utcnow()

        self.logger.info("Dashboard archived", dashboard_id=dashboard_id)

    def share_dashboard(
        self,
        dashboard_id: str,
        users: List[str],
        permission: str = "viewer",
    ) -> None:
        """
        Share dashboard with users.

        Args:
            dashboard_id: Dashboard identifier
            users: List of user IDs
            permission: Permission level (viewer, editor)
        """
        dashboard = self.get_dashboard(dashboard_id)

        if permission == "viewer":
            dashboard.access_control["viewers"].extend(users)
        elif permission == "editor":
            dashboard.access_control["editors"].extend(users)

        dashboard.updated_at = datetime.utcnow()

        self.logger.info(
            "Dashboard shared",
            dashboard_id=dashboard_id,
            users=len(users),
            permission=permission,
        )

    def clone_dashboard(
        self,
        dashboard_id: str,
        new_name: str,
        owner: str,
    ) -> Dashboard:
        """
        Clone existing dashboard.

        Args:
            dashboard_id: Dashboard to clone
            new_name: Name for new dashboard
            owner: Owner of new dashboard

        Returns:
            Cloned dashboard
        """
        source = self.get_dashboard(dashboard_id)

        # Create new dashboard
        new_dashboard = self.create_dashboard(
            name=new_name,
            description=f"Cloned from {source.name}",
            owner=owner,
            tags=source.tags.copy(),
        )

        # Copy data sources
        for ds in source.data_sources:
            self.add_data_source(
                dashboard_id=new_dashboard.dashboard_id,
                source_id=ds.source_id,
                name=ds.name,
                type=ds.type,
                connection_string=ds.connection_string,
                query=ds.query,
                file_path=ds.file_path,
                api_endpoint=ds.api_endpoint,
                refresh_interval=ds.refresh_interval,
                parameters=ds.parameters.copy(),
            )

        # Copy visualizations
        for viz in source.visualizations:
            self.add_visualization(
                dashboard_id=new_dashboard.dashboard_id,
                viz_id=viz.viz_id,
                name=viz.name,
                type=viz.type,
                data_source_id=viz.data_source_id,
                config=viz.config.copy(),
                position=viz.position.copy(),
            )

        self.logger.info(
            "Dashboard cloned",
            source_id=dashboard_id,
            new_id=new_dashboard.dashboard_id,
        )

        return new_dashboard

    def delete_dashboard(self, dashboard_id: str) -> None:
        """Delete dashboard."""
        if dashboard_id in self.dashboards:
            del self.dashboards[dashboard_id]

        self.logger.info("Dashboard deleted", dashboard_id=dashboard_id)

    def export_dashboard(self, dashboard_id: str) -> Dict[str, Any]:
        """Export dashboard as JSON."""
        dashboard = self.get_dashboard(dashboard_id)

        return {
            "dashboard_id": dashboard.dashboard_id,
            "name": dashboard.name,
            "description": dashboard.description,
            "owner": dashboard.owner,
            "status": dashboard.status.value,
            "data_sources": [
                {
                    "source_id": ds.source_id,
                    "name": ds.name,
                    "type": ds.type,
                    "connection_string": ds.connection_string,
                    "query": ds.query,
                    "parameters": ds.parameters,
                }
                for ds in dashboard.data_sources
            ],
            "visualizations": [
                {
                    "viz_id": viz.viz_id,
                    "name": viz.name,
                    "type": viz.type.value,
                    "data_source_id": viz.data_source_id,
                    "config": viz.config,
                    "position": viz.position,
                }
                for viz in dashboard.visualizations
            ],
            "tags": dashboard.tags,
            "created_at": dashboard.created_at.isoformat(),
            "updated_at": dashboard.updated_at.isoformat(),
        }
