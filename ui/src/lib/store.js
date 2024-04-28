import { writable } from 'svelte/store';
import {fetchAgentState, fetchMessages} from "$lib/api.js";

const getInitialSelectedProject = () => {
  if (typeof window !== 'undefined' && window.localStorage) {
    return localStorage.getItem('selectedProject') || '';
  }
  return '';
};

const getInitialSelectedModel = () => {
  if (typeof window !== 'undefined' && window.localStorage) {
    return localStorage.getItem('selectedModel') || '';
  }
  return '';
};

export const messages = writable([]);

export const selectedProject = writable(getInitialSelectedProject());
export const selectedModel = writable(getInitialSelectedModel());

export const projectList = writable([]);
export const modelList = writable({});
export const searchEngineList = writable([]);

export const agentState = writable(null);

export const internet = writable(true);
export const tokenUsage = writable(0);


selectedProject.subscribe((value) => {
  if (typeof window !== 'undefined' && window.localStorage) {
    localStorage.setItem('selectedProject', value);
  }
});

selectedModel.subscribe((value) => {
  if (typeof window !== 'undefined' && window.localStorage) {
    console.log("selectedModel subscriber: ", value)
    localStorage.setItem('selectedModel', value);
  }
});

export function selectProject(project) {
  localStorage.setItem("selectedProject", project);
  fetchMessages();
  fetchAgentState();
  document.getElementById("project-dropdown").classList.add("hidden");
  window.location.hash = encodeURIComponent(project);
}
