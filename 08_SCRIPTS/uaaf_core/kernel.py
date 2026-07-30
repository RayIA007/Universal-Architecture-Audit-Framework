"""
Kernel implementation for the Universal Architecture Audit Framework.

The UAAF Kernel is the public coordination facade of the framework core. It
validates audit execution requests, resolves profiles through the registry,
constructs the required domain and runtime objects, and delegates execution to
UAAFRuntime.

The Kernel does not execute processors directly, maintain mutable audit state,
construct advanced pipelines, discover plugins, or generate reports.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from uaaf_core.models.audit import Audit
from uaaf_core.models.profile import AuditProfile
from uaaf_core.models.session import AuditSession
from uaaf_core.registry import UAAFRegistry
from uaaf_core.runtime import RuntimeContext, UAAFRuntime


class UAAFKernel:
    """
    Coordinate the creation and execution of UAAF runtimes.

    One Kernel may create any number of independent audit runtimes. Runtime
    state remains isolated inside each RuntimeContext.

    Execution flow:

        Kernel
            ↓
        Registry profile resolution
            ↓
        Audit
            ↓
        AuditSession
            ↓
        RuntimeContext
            ↓
        UAAFRuntime
    """

    kernel_version = "1.0.0"

    def __init__(self, registry: UAAFRegistry) -> None:
        """
        Initialize the UAAF Kernel.

        Args:
            registry:
                Registry containing the profiles and processors available to
                runtime executions.
        """
        if not isinstance(registry, UAAFRegistry):
            raise TypeError(
                "UAAFKernel registry must be a UAAFRegistry instance, "
                f"received {type(registry).__name__}."
            )

        self._registry = registry

    @property
    def registry(self) -> UAAFRegistry:
        """
        Return the shared component registry.

        The Kernel does not own individual processors or profiles. It only
        uses this registry to resolve the components required by each runtime.
        """
        return self._registry

    def validate_profile(
        self,
        profile_id: str,
    ) -> AuditProfile:
        """
        Validate and return one executable audit profile.

        Validation confirms that:

        - the profile exists;
        - the profile is enabled;
        - the profile declares at least one processor;
        - all declared processors are registered.

        Args:
            profile_id:
                Identifier of the profile to validate.

        Returns:
            Validated AuditProfile.

        Raises:
            KeyError:
                If the profile is not registered.
            RuntimeError:
                If the profile cannot be executed.
        """
        normalized_profile_id = self._normalize_identifier(
            value=profile_id,
            field_name="profile identifier",
        )

        profile = self._registry.get_profile(normalized_profile_id)

        if not profile.enabled:
            raise RuntimeError(
                f"Audit profile {profile.id!r} is disabled."
            )

        if not profile.processor_ids:
            raise RuntimeError(
                f"Audit profile {profile.id!r} does not declare processors."
            )

        missing_processors = self._registry.validate_profile_dependencies(
            profile.id
        )

        if missing_processors:
            missing = ", ".join(
                repr(processor_id)
                for processor_id in missing_processors
            )

            raise RuntimeError(
                f"Audit profile {profile.id!r} has missing processor "
                f"dependencies: {missing}."
            )

        return profile

    def create_runtime(
        self,
        *,
        target_path: str | Path,
        profile_id: str,
        output_path: str | Path,
        workspace_path: str | Path,
        create_directories: bool = True,
        audit_metadata: dict[str, Any] | None = None,
        session_context: dict[str, Any] | None = None,
        runtime_metadata: dict[str, Any] | None = None,
    ) -> UAAFRuntime:
        """
        Build one independent UAAF runtime.

        This method constructs but does not initialize or execute the Runtime.

        Args:
            target_path:
                Project, repository, or artifact to audit.
            profile_id:
                Registered audit profile identifier.
            output_path:
                Directory in which final audit outputs will be written.
            workspace_path:
                Root directory used for temporary execution workspaces.
            create_directories:
                Whether output and workspace directories should be created.
            audit_metadata:
                Optional metadata assigned to the Audit.
            session_context:
                Optional values loaded into the AuditSession context.
            runtime_metadata:
                Optional values loaded into the RuntimeContext metadata.

        Returns:
            Newly created UAAFRuntime.

        Raises:
            FileNotFoundError:
                If the audit target does not exist.
            NotADirectoryError:
                If output or workspace paths point to regular files.
            RuntimeError:
                If the selected profile is not executable.
        """
        profile = self.validate_profile(profile_id)

        normalized_target_path = self._normalize_path(
            value=target_path,
            field_name="target path",
        )
        normalized_output_path = self._normalize_path(
            value=output_path,
            field_name="output path",
        )
        normalized_workspace_root = self._normalize_path(
            value=workspace_path,
            field_name="workspace path",
        )

        if not normalized_target_path.exists():
            raise FileNotFoundError(
                f"Audit target does not exist: "
                f"{normalized_target_path}."
            )

        if (
            normalized_output_path.exists()
            and not normalized_output_path.is_dir()
        ):
            raise NotADirectoryError(
                f"Audit output path is not a directory: "
                f"{normalized_output_path}."
            )

        if (
            normalized_workspace_root.exists()
            and not normalized_workspace_root.is_dir()
        ):
            raise NotADirectoryError(
                f"Audit workspace path is not a directory: "
                f"{normalized_workspace_root}."
            )

        if create_directories:
            normalized_output_path.mkdir(
                parents=True,
                exist_ok=True,
            )
            normalized_workspace_root.mkdir(
                parents=True,
                exist_ok=True,
            )

        audit = Audit(
            target_path=normalized_target_path,
            profile_id=profile.id,
            output_path=normalized_output_path,
        )

        self._load_audit_metadata(
            audit=audit,
            metadata=audit_metadata,
        )

        execution_workspace = (
            normalized_workspace_root / audit.id
        )

        if create_directories:
            execution_workspace.mkdir(
                parents=True,
                exist_ok=True,
            )

        session = AuditSession(
            audit=audit,
            workspace_path=execution_workspace,
        )

        self._load_session_context(
            session=session,
            values=session_context,
        )

        context = RuntimeContext(
            audit=audit,
            session=session,
            profile=profile,
            registry=self._registry,
        )

        context.set_metadata(
            "kernel_version",
            self.kernel_version,
        )
        context.set_metadata(
            "workspace_root",
            str(normalized_workspace_root),
        )
        context.set_metadata(
            "execution_workspace",
            str(execution_workspace),
        )

        self._load_runtime_metadata(
            context=context,
            metadata=runtime_metadata,
        )

        return UAAFRuntime(context)

    def run_audit(
        self,
        *,
        target_path: str | Path,
        profile_id: str,
        output_path: str | Path,
        workspace_path: str | Path,
        create_directories: bool = True,
        audit_metadata: dict[str, Any] | None = None,
        session_context: dict[str, Any] | None = None,
        runtime_metadata: dict[str, Any] | None = None,
    ) -> UAAFRuntime:
        """
        Create and execute one complete UAAF runtime.

        The returned Runtime contains the final Audit, AuditSession,
        RuntimeContext, ProcessorResults, metrics, and execution metadata.

        Any execution exception is propagated after the Runtime marks the
        audit and session as failed.

        Returns:
            Terminal UAAFRuntime.
        """
        runtime = self.create_runtime(
            target_path=target_path,
            profile_id=profile_id,
            output_path=output_path,
            workspace_path=workspace_path,
            create_directories=create_directories,
            audit_metadata=audit_metadata,
            session_context=session_context,
            runtime_metadata=runtime_metadata,
        )

        runtime.run()
        return runtime

    def create_context(
        self,
        *,
        audit: Audit,
        session: AuditSession,
        profile_id: str,
        runtime_metadata: dict[str, Any] | None = None,
    ) -> RuntimeContext:
        """
        Create a RuntimeContext from existing domain objects.

        This entry point is useful for adapters, tests, restored executions,
        or integrations that construct Audit and AuditSession externally.

        Args:
            audit:
                Existing audit instance.
            session:
                Existing session associated with the audit.
            profile_id:
                Registered profile identifier.
            runtime_metadata:
                Optional RuntimeContext metadata.

        Returns:
            Validated RuntimeContext.
        """
        if not isinstance(audit, Audit):
            raise TypeError(
                "UAAFKernel audit must be an Audit instance, "
                f"received {type(audit).__name__}."
            )

        if not isinstance(session, AuditSession):
            raise TypeError(
                "UAAFKernel session must be an AuditSession instance, "
                f"received {type(session).__name__}."
            )

        profile = self.validate_profile(profile_id)

        if audit.profile_id != profile.id:
            raise ValueError(
                f"Audit profile_id {audit.profile_id!r} does not match "
                f"requested profile {profile.id!r}."
            )

        context = RuntimeContext(
            audit=audit,
            session=session,
            profile=profile,
            registry=self._registry,
        )

        context.set_metadata(
            "kernel_version",
            self.kernel_version,
        )

        self._load_runtime_metadata(
            context=context,
            metadata=runtime_metadata,
        )

        return context

    def create_runtime_from_context(
        self,
        context: RuntimeContext,
    ) -> UAAFRuntime:
        """
        Create a Runtime around an existing RuntimeContext.

        The context must use the same Registry instance as this Kernel.
        """
        if not isinstance(context, RuntimeContext):
            raise TypeError(
                "UAAFKernel context must be a RuntimeContext instance, "
                f"received {type(context).__name__}."
            )

        if context.registry is not self._registry:
            raise ValueError(
                "RuntimeContext registry does not belong to this Kernel."
            )

        self.validate_profile(context.profile_id)

        context.set_metadata(
            "kernel_version",
            self.kernel_version,
        )

        return UAAFRuntime(context)

    def snapshot(self) -> dict[str, Any]:
        """
        Return a serializable Kernel summary.

        The Kernel snapshot contains no audit execution state.
        """
        registry_snapshot = self._registry.snapshot()

        return {
            "kernel_version": self.kernel_version,
            "registry": registry_snapshot,
        }

    @staticmethod
    def _load_audit_metadata(
        *,
        audit: Audit,
        metadata: dict[str, Any] | None,
    ) -> None:
        """Load optional Audit metadata."""
        if metadata is None:
            return

        if not isinstance(metadata, dict):
            raise TypeError(
                "UAAFKernel audit_metadata must be a dictionary, "
                f"received {type(metadata).__name__}."
            )

        for key, value in metadata.items():
            normalized_key = UAAFKernel._normalize_identifier(
                value=key,
                field_name="audit metadata key",
            )
            audit.set_metadata(normalized_key, value)

    @staticmethod
    def _load_session_context(
        *,
        session: AuditSession,
        values: dict[str, Any] | None,
    ) -> None:
        """Load optional AuditSession context values."""
        if values is None:
            return

        if not isinstance(values, dict):
            raise TypeError(
                "UAAFKernel session_context must be a dictionary, "
                f"received {type(values).__name__}."
            )

        for key, value in values.items():
            normalized_key = UAAFKernel._normalize_identifier(
                value=key,
                field_name="session context key",
            )
            session.set_context(normalized_key, value)

    @staticmethod
    def _load_runtime_metadata(
        *,
        context: RuntimeContext,
        metadata: dict[str, Any] | None,
    ) -> None:
        """Load optional RuntimeContext metadata."""
        if metadata is None:
            return

        if not isinstance(metadata, dict):
            raise TypeError(
                "UAAFKernel runtime_metadata must be a dictionary, "
                f"received {type(metadata).__name__}."
            )

        for key, value in metadata.items():
            normalized_key = UAAFKernel._normalize_identifier(
                value=key,
                field_name="runtime metadata key",
            )
            context.set_metadata(normalized_key, value)

    @staticmethod
    def _normalize_identifier(
        *,
        value: str,
        field_name: str,
    ) -> str:
        """Validate and normalize a required Kernel identifier."""
        if not isinstance(value, str):
            raise TypeError(
                f"UAAFKernel {field_name} must be a string, "
                f"received {type(value).__name__}."
            )

        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError(
                f"UAAFKernel {field_name} cannot be empty."
            )

        return normalized_value

    @staticmethod
    def _normalize_path(
        *,
        value: str | Path,
        field_name: str,
    ) -> Path:
        """Validate and normalize a filesystem path."""
        if isinstance(value, str):
            normalized_value = value.strip()

            if not normalized_value:
                raise ValueError(
                    f"UAAFKernel {field_name} cannot be empty."
                )

            path = Path(normalized_value)
        elif isinstance(value, Path):
            path = value
        else:
            raise TypeError(
                f"UAAFKernel {field_name} must be a string or Path, "
                f"received {type(value).__name__}."
            )

        return path.expanduser().resolve()