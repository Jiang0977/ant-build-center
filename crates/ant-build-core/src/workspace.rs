use std::fs;
use std::io;
use std::path::Path;

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Workspace {
    pub version: u32,
    pub runtime: RuntimeSettings,
    #[serde(default)]
    pub groups: Vec<GroupRecord>,
    pub projects: Vec<ProjectRecord>,
}

#[derive(Debug, Clone, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct RuntimeSettings {
    #[serde(alias = "java_home")]
    pub java_home: String,
    #[serde(alias = "ant_home")]
    pub ant_home: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct GroupRecord {
    pub id: String,
    pub name: String,
    #[serde(default = "default_true")]
    pub expanded: bool,
    #[serde(default)]
    pub system: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ProjectRecord {
    pub id: String,
    pub path: String,
    pub name: String,
    #[serde(alias = "default_target")]
    pub default_target: String,
    pub targets: Vec<String>,
    #[serde(alias = "last_status")]
    pub last_status: String,
    #[serde(alias = "last_run_at")]
    pub last_run_at: Option<String>,
    #[serde(default = "default_group_id", alias = "group_id")]
    pub group_id: String,
    #[serde(default, alias = "order")]
    pub order: usize,
}

impl Default for Workspace {
    fn default() -> Self {
        Self {
            version: 3,
            runtime: RuntimeSettings::default(),
            groups: vec![default_group()],
            projects: Vec::new(),
        }
    }
}

pub fn load_workspace(path: &Path) -> io::Result<Workspace> {
    if !path.exists() {
        return Ok(Workspace::default());
    }

    let content = fs::read_to_string(path)?;
    let mut workspace: Workspace = serde_json::from_str(&content)
        .map_err(|error| io::Error::new(io::ErrorKind::InvalidData, error))?;
    workspace.normalize();
    Ok(workspace)
}

pub fn save_workspace(path: &Path, workspace: &Workspace) -> io::Result<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }

    let payload = serde_json::to_string_pretty(workspace)
        .map_err(|error| io::Error::new(io::ErrorKind::InvalidData, error))?;
    fs::write(path, payload)
}

impl Workspace {
    pub fn create_group(&mut self, group_id: impl Into<String>, name: &str) -> Result<(), String> {
        let group_id = group_id.into();
        let name = name.trim();

        if group_id.trim().is_empty() {
            return Err("Group id cannot be empty.".to_string());
        }
        if name.is_empty() {
            return Err("Group name cannot be empty.".to_string());
        }
        if self.groups.iter().any(|group| group.id == group_id) {
            return Err("Group already exists.".to_string());
        }

        self.groups.push(GroupRecord {
            id: group_id,
            name: name.to_string(),
            expanded: true,
            system: false,
        });
        Ok(())
    }

    pub fn rename_group(&mut self, group_id: &str, name: &str) -> Result<(), String> {
        let name = name.trim();
        if name.is_empty() {
            return Err("Group name cannot be empty.".to_string());
        }

        let group = self
            .groups
            .iter_mut()
            .find(|group| group.id == group_id)
            .ok_or_else(|| "Group not found.".to_string())?;

        if group.system {
            return Err("System groups cannot be renamed.".to_string());
        }

        group.name = name.to_string();
        Ok(())
    }

    pub fn set_group_expanded(&mut self, group_id: &str, expanded: bool) -> Result<(), String> {
        let group = self
            .groups
            .iter_mut()
            .find(|group| group.id == group_id)
            .ok_or_else(|| "Group not found.".to_string())?;
        group.expanded = expanded;
        Ok(())
    }

    pub fn delete_group(&mut self, group_id: &str) -> Result<(), String> {
        if group_id == default_group_id_ref() {
            return Err("System groups cannot be deleted.".to_string());
        }

        let group = self
            .groups
            .iter()
            .find(|group| group.id == group_id)
            .ok_or_else(|| "Group not found.".to_string())?;

        if group.system {
            return Err("System groups cannot be deleted.".to_string());
        }

        for project in &mut self.projects {
            if project.group_id == group_id {
                project.group_id = default_group_id();
            }
        }

        self.groups.retain(|group| group.id != group_id);
        normalize_project_order(&mut self.projects);
        Ok(())
    }

    pub fn add_project_to_group(
        &mut self,
        mut project: ProjectRecord,
        group_id: &str,
    ) -> Result<(), String> {
        if !self.groups.iter().any(|group| group.id == group_id) {
            return Err("Group not found.".to_string());
        }
        if self
            .projects
            .iter()
            .any(|existing| existing.path == project.path)
        {
            return Ok(());
        }

        project.group_id = group_id.to_string();
        project.order = self
            .projects
            .iter()
            .filter(|existing| existing.group_id == group_id)
            .count();
        self.projects.push(project);
        Ok(())
    }

    pub fn remove_project(&mut self, project_id: &str) -> Result<(), String> {
        self.remove_projects(&[project_id.to_string()])
    }

    pub fn remove_projects(&mut self, project_ids: &[String]) -> Result<(), String> {
        if project_ids.is_empty() {
            return Ok(());
        }
        if !project_ids.iter().all(|project_id| {
            self.projects
                .iter()
                .any(|project| project.id == *project_id)
        }) {
            return Err("Project not found.".to_string());
        }

        let removed_ids = project_ids
            .iter()
            .map(|id| id.as_str())
            .collect::<std::collections::BTreeSet<_>>();

        self.projects
            .retain(|project| !removed_ids.contains(project.id.as_str()));
        normalize_project_order(&mut self.projects);
        Ok(())
    }

    pub fn move_projects(
        &mut self,
        project_ids: &[String],
        target_group_id: &str,
        target_index: usize,
    ) -> Result<(), String> {
        if !self.groups.iter().any(|group| group.id == target_group_id) {
            return Err("Group not found.".to_string());
        }
        if project_ids.is_empty() {
            return Ok(());
        }

        let moving_ids = project_ids
            .iter()
            .map(|id| id.as_str())
            .collect::<std::collections::BTreeSet<_>>();
        if !project_ids.iter().all(|project_id| {
            self.projects
                .iter()
                .any(|project| project.id == *project_id)
        }) {
            return Err("Project not found.".to_string());
        }

        let mut ordered_by_group = self.group_project_ids_excluding(&moving_ids);
        let target_ids = ordered_by_group
            .entry(target_group_id.to_string())
            .or_default();
        let insertion_index = target_index.min(target_ids.len());
        target_ids.splice(
            insertion_index..insertion_index,
            project_ids.iter().cloned(),
        );

        for project in &mut self.projects {
            if moving_ids.contains(project.id.as_str()) {
                project.group_id = target_group_id.to_string();
            }
        }

        self.apply_group_project_order(&ordered_by_group);
        Ok(())
    }

    fn normalize(&mut self) {
        if self.version < 3 {
            self.version = 3;
        }

        ensure_default_group(&mut self.groups);

        for project in &mut self.projects {
            if !self.groups.iter().any(|group| group.id == project.group_id) {
                project.group_id = default_group_id();
            }
        }

        deduplicate_project_paths(&mut self.projects);
        normalize_project_order(&mut self.projects);
    }

    fn group_project_ids_excluding(
        &self,
        excluded_ids: &std::collections::BTreeSet<&str>,
    ) -> std::collections::BTreeMap<String, Vec<String>> {
        let mut ordered_by_group = std::collections::BTreeMap::<String, Vec<String>>::new();

        for group in &self.groups {
            let mut ids = self
                .projects
                .iter()
                .filter(|project| {
                    project.group_id == group.id && !excluded_ids.contains(project.id.as_str())
                })
                .collect::<Vec<_>>();
            ids.sort_by_key(|project| project.order);
            ordered_by_group.insert(
                group.id.clone(),
                ids.into_iter().map(|project| project.id.clone()).collect(),
            );
        }

        ordered_by_group
    }

    fn apply_group_project_order(
        &mut self,
        ordered_by_group: &std::collections::BTreeMap<String, Vec<String>>,
    ) {
        let mut positions = std::collections::BTreeMap::<String, (String, usize)>::new();
        for (group_id, project_ids) in ordered_by_group {
            for (order, project_id) in project_ids.iter().enumerate() {
                positions.insert(project_id.clone(), (group_id.clone(), order));
            }
        }

        for project in &mut self.projects {
            if let Some((group_id, order)) = positions.get(&project.id) {
                project.group_id = group_id.clone();
                project.order = *order;
            }
        }
    }
}

fn ensure_default_group(groups: &mut Vec<GroupRecord>) {
    if let Some(group) = groups
        .iter_mut()
        .find(|group| group.id == default_group_id())
    {
        group.name = default_group_name().to_string();
        group.system = true;
        return;
    }

    groups.insert(0, default_group());
}

fn normalize_project_order(projects: &mut [ProjectRecord]) {
    let mut grouped_indices = std::collections::BTreeMap::<String, Vec<(usize, usize)>>::new();

    for (index, project) in projects.iter().enumerate() {
        grouped_indices
            .entry(project.group_id.clone())
            .or_default()
            .push((project.order, index));
    }

    for entries in grouped_indices.values_mut() {
        entries.sort_by_key(|(order, index)| (*order, *index));
        for (normalized_order, (_, project_index)) in entries.iter().enumerate() {
            projects[*project_index].order = normalized_order;
        }
    }
}

fn deduplicate_project_paths(projects: &mut Vec<ProjectRecord>) {
    let mut seen_paths = std::collections::BTreeSet::<String>::new();
    projects.retain(|project| seen_paths.insert(project.path.clone()));
}

fn default_group() -> GroupRecord {
    GroupRecord {
        id: default_group_id(),
        name: default_group_name().to_string(),
        expanded: true,
        system: true,
    }
}

fn default_group_id() -> String {
    default_group_id_ref().to_string()
}

fn default_group_id_ref() -> &'static str {
    "default"
}

fn default_group_name() -> &'static str {
    "Ungrouped"
}

fn default_true() -> bool {
    true
}
